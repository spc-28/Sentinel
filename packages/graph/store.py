"""The service dependency map: record links, query blast radius, prune stale edges.

Nodes are ``(:Service {name})`` and edges ``[:DEPENDS_ON {kind, last_seen}]`` where
source DEPENDS_ON target (source calls/reads target). Edges carry a ``last_seen``
timestamp; queries ignore edges older than ``FADE_DAYS`` and ``prune_stale`` deletes them.
"""

from __future__ import annotations

import structlog

from packages.graph.client import execute, fetch
from packages.graph.topology import SPAN_TARGETS, TOPOLOGY
from packages.tools.common import KNOWN_SERVICES
from packages.tools.traces import find_slow_traces, get_trace

log = structlog.get_logger()

FADE_DAYS = 7
_FRESH = f"r.last_seen >= datetime() - duration({{days: {FADE_DAYS}}})"


async def record_dependency(source: str, target: str, kind: str = "CALLS") -> None:
    """Upsert an edge source→target and refresh its last_seen timestamp."""
    await execute(
        """
        MERGE (a:Service {name: $source})
        MERGE (b:Service {name: $target})
        MERGE (a)-[r:DEPENDS_ON {kind: $kind}]->(b)
        SET r.last_seen = datetime()
        """,
        source=source,
        target=target,
        kind=kind,
    )


def _hops(max_hops: int) -> int:
    return max(1, min(max_hops, 3))  # bound the traversal


async def blast_radius(service: str, max_hops: int = 2) -> list[str]:
    """Downstream services ``service`` depends on (what its failure touches)."""
    rows = await fetch(
        f"""
        MATCH path = (s:Service {{name: $name}})-[:DEPENDS_ON*1..{_hops(max_hops)}]->(d:Service)
        WHERE all(r IN relationships(path) WHERE {_FRESH})
        RETURN DISTINCT d.name AS name
        """,
        name=service,
    )
    return sorted(row["name"] for row in rows)


async def dependents(service: str, max_hops: int = 2) -> list[str]:
    """Upstream services that depend on ``service`` (who is affected if it breaks)."""
    rows = await fetch(
        f"""
        MATCH path = (d:Service)-[:DEPENDS_ON*1..{_hops(max_hops)}]->(s:Service {{name: $name}})
        WHERE all(r IN relationships(path) WHERE {_FRESH})
        RETURN DISTINCT d.name AS name
        """,
        name=service,
    )
    return sorted(row["name"] for row in rows)


async def neighbors(service: str) -> set[str]:
    """Directly connected services (either direction), used by alert correlation."""
    rows = await fetch(
        f"""
        MATCH (s:Service {{name: $name}})-[r:DEPENDS_ON]-(n:Service)
        WHERE {_FRESH}
        RETURN DISTINCT n.name AS name
        """,
        name=service,
    )
    return {row["name"] for row in rows}


async def prune_stale(days: int = FADE_DAYS) -> None:
    await execute(
        "MATCH ()-[r:DEPENDS_ON]->() "
        "WHERE r.last_seen < datetime() - duration({days: $days}) DELETE r",
        days=days,
    )


async def seed_dependencies() -> int:
    """Write the canonical fake topology (idempotent). Returns the edge count."""
    for source, target, kind in TOPOLOGY:
        await record_dependency(source, target, kind)
    log.info("graph.seeded", edges=len(TOPOLOGY))
    return len(TOPOLOGY)


async def build_from_traces(lookback_minutes: int = 360, *, per_service: int = 50) -> int:
    """Infer edges from recent traces: for each call/read span, record source→target."""
    recorded = 0
    for service in KNOWN_SERVICES:
        summaries = find_slow_traces(service, slower_than_ms=0, last_n_minutes=lookback_minutes)
        for summary in summaries[:per_service]:
            trace = get_trace(summary.trace_id)
            edges = {
                SPAN_TARGETS[span.name]
                for span in trace.spans
                if span.name in SPAN_TARGETS and SPAN_TARGETS[span.name][0] != service
            }
            for target, kind in edges:
                await record_dependency(service, target, kind)
                recorded += 1
    log.info("graph.built_from_traces", edges_recorded=recorded)
    return recorded
