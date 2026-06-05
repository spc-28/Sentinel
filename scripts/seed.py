"""Seed the database with sample services and runbooks for local testing.

Idempotent: services are keyed by name and runbooks by title, so re-running
won't create duplicates. Run with: `make seed` (or `uv run python -m scripts.seed`).
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from packages.core.db import session_factory
from packages.core.logging import configure_logging
from packages.core.repositories import RunbookRepository, ServiceRepository

SERVICES: list[dict[str, str]] = [
    {
        "name": "checkout-api",
        "team": "payments",
        "repo_url": "https://github.com/acme/checkout-api",
        "description": "Handles cart checkout and payment authorization.",
    },
    {
        "name": "auth-service",
        "team": "identity",
        "repo_url": "https://github.com/acme/auth-service",
        "description": "Login, sessions and token issuance.",
    },
    {
        "name": "search-api",
        "team": "discovery",
        "repo_url": "https://github.com/acme/search-api",
        "description": "Product search and autocomplete.",
    },
    {
        "name": "notifications-worker",
        "team": "growth",
        "repo_url": "https://github.com/acme/notifications-worker",
        "description": "Sends email and push notifications.",
    },
    {
        "name": "inventory-service",
        "team": "supply-chain",
        "repo_url": "https://github.com/acme/inventory-service",
        "description": "Tracks stock levels and reservations.",
    },
]

RUNBOOKS: list[dict[str, Any]] = [
    {
        "title": "High API latency",
        "content": "Check upstream DB latency, connection pool saturation and recent deploys.",
        "tags": ["latency", "performance", "api"],
    },
    {
        "title": "Database connection pool exhausted",
        "content": "Inspect open connections, look for leaked sessions, raise pool size if needed.",
        "tags": ["database", "postgres", "connections"],
    },
    {
        "title": "Elevated 5xx error rate",
        "content": "Correlate with deploy timeline, inspect error logs, roll back if regression.",
        "tags": ["errors", "5xx", "reliability"],
    },
    {
        "title": "Redis memory pressure",
        "content": "Check eviction stats and key growth; review TTLs and large keys.",
        "tags": ["redis", "memory", "cache"],
    },
    {
        "title": "Payment provider timeouts",
        "content": "Verify provider status page, check circuit breaker, enable fallback provider.",
        "tags": ["payments", "timeouts", "third-party"],
    },
    {
        "title": "Authentication failures spike",
        "content": "Check token signing key rotation and clock skew across nodes.",
        "tags": ["auth", "tokens", "identity"],
    },
    {
        "title": "Search results stale",
        "content": "Confirm indexer is running and the ingestion lag is within bounds.",
        "tags": ["search", "indexing", "freshness"],
    },
    {
        "title": "Notification backlog growing",
        "content": "Inspect queue depth and worker concurrency; scale workers if needed.",
        "tags": ["queue", "workers", "backlog"],
    },
    {
        "title": "Disk space low",
        "content": "Identify large files/logs, rotate or prune, expand volume if persistent.",
        "tags": ["disk", "storage", "infra"],
    },
    {
        "title": "Deploy rollback procedure",
        "content": "Identify last good revision, trigger rollback, verify health checks recover.",
        "tags": ["deploy", "rollback", "release"],
    },
]


async def seed() -> None:
    configure_logging()
    log = structlog.get_logger()

    async with session_factory() as session:
        services = ServiceRepository(session)
        created_services = 0
        for data in SERVICES:
            if await services.get_by_name(data["name"]) is None:
                await services.create(**data)
                created_services += 1

        runbooks = RunbookRepository(session)
        created_runbooks = 0
        for data in RUNBOOKS:
            if await runbooks.get_by_title(data["title"]) is None:
                await runbooks.create(**data)
                created_runbooks += 1

        await session.commit()

    log.info(
        "seed.done",
        services_created=created_services,
        runbooks_created=created_runbooks,
    )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
