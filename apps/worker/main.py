"""Sentinel worker — consumes jobs from the Redis queue and dispatches them.

Also keeps the Neo4j service dependency map warm: seeds it on startup and refreshes
it hourly in the background.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import redis.asyncio as redis
import structlog
from packages.agents.ai_pipeline.detectors import run_all_detectors
from packages.agents.observability import configure_observability
from packages.core.config import get_settings
from packages.core.db import dispose_engine
from packages.core.logging import configure_logging
from packages.core.queue import JobQueue
from packages.graph.client import close_driver
from packages.graph.refresh import refresh_map
from packages.graph.store import seed_dependencies
from packages.memory.patterns import merge_patterns
from packages.rag import store as rag_store
from packages.rag.logs_index import index_recent_logs
from packages.tools.common import KNOWN_SERVICES

from apps.worker.jobs.investigate import handle_investigate, recover_running

log = structlog.get_logger()

_REFRESH_SECONDS = 3600
_LOG_INDEX_SECONDS = 300
_AI_DETECTOR_SECONDS = 3600


async def _dispatch(job: dict[str, Any]) -> None:
    job_type = job.get("type")
    payload = job.get("payload", {})
    if job_type == "investigate_alert":
        alert_id = payload.get("alert_id")
        if not alert_id:
            log.warning("worker.job_missing_alert_id", job=job)
            return
        await handle_investigate(alert_id)
    else:
        log.warning("worker.unknown_job", job_type=job_type)


async def _graph_refresh_loop() -> None:
    """Hourly: rebuild the dependency map from traces and prune stale edges."""
    while True:
        await asyncio.sleep(_REFRESH_SECONDS)
        try:
            await refresh_map()
        except Exception as exc:  # noqa: BLE001 - graph optional
            log.error("worker.graph_refresh_failed", error=str(exc))


async def _log_index_loop() -> None:
    """Every 5 minutes: embed new logs into Qdrant over the rolling window."""
    while True:
        try:
            await index_recent_logs()
        except Exception as exc:  # noqa: BLE001 - RAG optional
            log.error("worker.log_index_failed", error=str(exc))
        await asyncio.sleep(_LOG_INDEX_SECONDS)


async def _ai_detector_loop() -> None:
    """Hourly: run the AI-pipeline detectors (embedding drift, RAG quality, cost, prompt)."""
    while True:
        try:
            await run_all_detectors(indexes=["runbooks"], services=list(KNOWN_SERVICES))
        except Exception as exc:  # noqa: BLE001 - detectors optional
            log.error("worker.ai_detectors_failed", error=str(exc))
        await asyncio.sleep(_AI_DETECTOR_SECONDS)


async def _memory_merge_loop() -> None:
    """Periodically merge similar past incidents into reusable patterns."""
    interval = get_settings().memory_merge_seconds
    while True:
        await asyncio.sleep(interval)
        try:
            await merge_patterns()
        except Exception as exc:  # noqa: BLE001 - memory optional
            log.error("worker.memory_merge_failed", error=str(exc))


async def run() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    queue = JobQueue(redis_client)
    configure_observability()  # LiteLLM cost tracking + Langfuse tracing (if keys set)
    log.info("worker.startup", environment=settings.environment)

    try:
        await seed_dependencies()  # ensure the map exists even without real traces
    except Exception as exc:  # noqa: BLE001 - graph optional
        log.error("worker.graph_seed_failed", error=str(exc))

    await recover_running()  # resume investigations interrupted by a previous crash
    refresh_task = asyncio.create_task(_graph_refresh_loop())
    log_index_task = asyncio.create_task(_log_index_loop())
    ai_detector_task = asyncio.create_task(_ai_detector_loop())
    memory_merge_task = asyncio.create_task(_memory_merge_loop())
    try:
        while True:
            job = await queue.dequeue(block_seconds=5)
            if job is None:
                continue
            try:
                await _dispatch(job)
            except Exception as exc:  # noqa: BLE001 - one bad job shouldn't kill the worker
                log.error("worker.job_failed", error=str(exc), job=job)
    except asyncio.CancelledError:
        log.info("worker.shutdown")
        raise
    finally:
        for task in (refresh_task, log_index_task, ai_detector_task, memory_merge_task):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await redis_client.aclose()
        await dispose_engine()
        await close_driver()
        await rag_store.close()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()
