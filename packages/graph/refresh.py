"""Periodic refresh of the dependency map: rebuild from traces, drop stale edges."""

from __future__ import annotations

import structlog

from packages.graph.store import build_from_traces, prune_stale

log = structlog.get_logger()


async def refresh_map() -> int:
    """Rebuild edges from recent traces and prune anything not seen in 7 days."""
    recorded = await build_from_traces()
    await prune_stale()
    log.info("graph.refreshed", edges_recorded=recorded)
    return recorded
