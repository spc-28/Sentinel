"""A minimal Redis-backed job queue (a single list consumed FIFO)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import redis.asyncio as redis
import structlog

log = structlog.get_logger()

DEFAULT_QUEUE_KEY = "sentinel:jobs"


class JobQueue:
    def __init__(self, client: redis.Redis, *, key: str = DEFAULT_QUEUE_KEY) -> None:
        self._client = client
        self._key = key

    async def enqueue(self, job_type: str, payload: dict[str, Any]) -> str:
        """Push a job onto the queue and return its id."""
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "type": job_type,
            "payload": payload,
            "enqueued_at": datetime.now(UTC).isoformat(),
        }
        await self._client.lpush(self._key, json.dumps(job))
        log.info("queue.enqueued", job_id=job_id, job_type=job_type, queue=self._key)
        return job_id

    async def dequeue(self, *, block_seconds: int = 5) -> dict[str, Any] | None:
        """Block up to ``block_seconds`` for the next job (requires a string client)."""
        item = await self._client.brpop([self._key], timeout=block_seconds)
        if item is None:
            return None
        _key, raw = cast(tuple[str, str], item)
        return cast(dict[str, Any], json.loads(raw))
