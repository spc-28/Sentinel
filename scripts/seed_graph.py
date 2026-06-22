"""Seed the Neo4j service dependency map with the canonical fake topology."""

from __future__ import annotations

import asyncio

import structlog
from packages.core.logging import configure_logging
from packages.graph.client import close_driver
from packages.graph.store import seed_dependencies

log = structlog.get_logger()


async def main() -> None:
    configure_logging()
    edges = await seed_dependencies()
    await close_driver()
    log.info("graph.seed_done", edges=edges)


if __name__ == "__main__":
    asyncio.run(main())
