"""Embed recent error logs into Qdrant over a rolling window (background job)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from packages.core.config import get_settings
from packages.rag import store
from packages.rag.embeddings import embed
from packages.tools.common import KNOWN_SERVICES
from packages.tools.logs import get_recent_errors

log = structlog.get_logger()

_PER_SERVICE = 50


async def index_recent_logs() -> int:
    """Embed new error logs for each service; prune anything past the window."""
    settings = get_settings()
    now = datetime.now(UTC)

    points: list[tuple[str, str, dict[str, object]]] = []
    for service in KNOWN_SERVICES:
        for entry in get_recent_errors(service, _PER_SERVICE):
            key = f"{service}:{entry.message}:{entry.timestamp.isoformat()}"
            chunk_id = store.point_id(key)
            points.append(
                (
                    chunk_id,
                    f"{service}: {entry.message}",
                    {
                        "service": service,
                        "message": entry.message,
                        "ts": entry.timestamp.timestamp(),
                    },
                )
            )

    await store.ensure_collection(store.LOGS)
    already = await store.existing_ids(store.LOGS, [p[0] for p in points])
    fresh = [p for p in points if p[0] not in already]
    vectors = embed([text for _, text, _ in fresh])
    await store.upsert(
        store.LOGS,
        [(pid, vec, payload) for (pid, _, payload), vec in zip(fresh, vectors, strict=True)],
    )

    cutoff = (now - timedelta(days=settings.log_index_window_days)).timestamp()
    await store.prune_older_than(store.LOGS, cutoff)

    log.info("logs.indexed", new=len(fresh), skipped=len(points) - len(fresh))
    return len(fresh)
