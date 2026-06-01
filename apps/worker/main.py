"""Sentinel worker — background process skeleton.

For now this is a heartbeat loop that proves the worker starts, loads settings
and logs cleanly. Real investigation jobs (consuming from the Redis queue) are
added in a later milestone.
"""

from __future__ import annotations

import asyncio
import contextlib

import structlog
from packages.core.config import get_settings
from packages.core.logging import configure_logging

log = structlog.get_logger()

_HEARTBEAT_SECONDS = 15


async def run() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    log.info("worker.startup", environment=settings.environment)
    try:
        while True:
            log.debug("worker.heartbeat")
            await asyncio.sleep(_HEARTBEAT_SECONDS)
    except asyncio.CancelledError:
        log.info("worker.shutdown")
        raise


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()
