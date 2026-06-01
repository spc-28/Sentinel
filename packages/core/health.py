"""Connectivity checks for backing services, used by the API readiness probe."""

from __future__ import annotations

import asyncpg
import redis.asyncio as redis
import structlog

from packages.core.config import Settings

log = structlog.get_logger()

_TIMEOUT_SECONDS = 3.0


async def check_postgres(settings: Settings) -> bool:
    """Return ``True`` if a trivial query succeeds against Postgres."""
    try:
        conn = await asyncpg.connect(dsn=settings.postgres_dsn, timeout=_TIMEOUT_SECONDS)
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        log.warning("healthcheck.postgres_failed", error=str(exc))
        return False
    return True


async def check_redis(settings: Settings) -> bool:
    """Return ``True`` if Redis responds to PING."""
    client = redis.from_url(settings.redis_url, socket_connect_timeout=_TIMEOUT_SECONDS)
    try:
        return bool(await client.ping())
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        log.warning("healthcheck.redis_failed", error=str(exc))
        return False
    finally:
        await client.aclose()
