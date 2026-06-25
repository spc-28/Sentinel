"""Sentinel API — entrypoint exposing liveness and readiness probes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Response, status
from packages.core.config import get_settings
from packages.core.db import dispose_engine
from packages.core.health import check_postgres, check_redis
from packages.core.logging import configure_logging
from packages.core.queue import JobQueue

from apps.api.routers import incident_groups, incidents, investigations, webhooks

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis_client
    app.state.queue = JobQueue(redis_client)

    log.info("api.startup", environment=settings.environment)
    yield
    await redis_client.aclose()
    await dispose_engine()
    log.info("api.shutdown")


app = FastAPI(title="Sentinel API", version="0.1.0", lifespan=lifespan)
app.include_router(webhooks.router)
app.include_router(investigations.router)
app.include_router(incident_groups.router)
app.include_router(incidents.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: the process is up and serving requests."""
    return {"status": "ok"}


@app.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    """Readiness probe: backing services (Postgres, Redis) are reachable."""
    settings = get_settings()
    postgres_ok = await check_postgres(settings)
    redis_ok = await check_redis(settings)
    ready = postgres_ok and redis_ok

    response.status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {"postgres": postgres_ok, "redis": redis_ok},
    }
