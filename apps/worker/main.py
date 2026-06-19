"""Sentinel worker — consumes jobs from the Redis queue and dispatches them."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import redis.asyncio as redis
import structlog
from packages.core.config import get_settings
from packages.core.db import dispose_engine
from packages.core.logging import configure_logging
from packages.core.queue import JobQueue

from apps.worker.jobs.investigate import handle_investigate, recover_running

log = structlog.get_logger()


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


async def run() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    queue = JobQueue(redis_client)
    log.info("worker.startup", environment=settings.environment)
    await recover_running()  # resume investigations interrupted by a previous crash
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
        await redis_client.aclose()
        await dispose_engine()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()
