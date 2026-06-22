"""Async Neo4j driver management (one shared driver per process)."""

from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from packages.core.config import get_settings

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def execute(cypher: str, **params: Any) -> None:
    """Run a write query (auto-commit)."""
    async with get_driver().session() as session:
        result = await session.run(cypher, params)
        await result.consume()


async def fetch(cypher: str, **params: Any) -> list[dict[str, Any]]:
    """Run a read query and return the rows as dicts."""
    async with get_driver().session() as session:
        result = await session.run(cypher, params)
        return [record.data() async for record in result]
