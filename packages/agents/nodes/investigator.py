"""Investigator — gathers evidence from the Part 3 tools.

Deterministic on purpose: round 1 collects the headline signals; later rounds
(triggered by the verifier retry loop) dig deeper into traces and recent errors.
"""

from __future__ import annotations

import structlog

from packages.agents.state import EvidenceItem, GraphState
from packages.tools.deploys import recent_deploys
from packages.tools.logs import get_recent_errors, summarize_logs
from packages.tools.metrics import get_p95_latency, is_anomaly
from packages.tools.traces import find_error_traces, find_slow_traces

log = structlog.get_logger()


def _first_round(service: str) -> list[EvidenceItem]:
    summary = summarize_logs(service, 60)
    latency = get_p95_latency(service, 60)
    anomaly = is_anomaly(service, "latency_ms", 30)
    deploys = recent_deploys(service, 1440)
    return [
        EvidenceItem(
            source="logs",
            summary=f"{summary.total} logs, error_rate {summary.error_rate}",
            detail="top errors: " + ", ".join(e.message for e in summary.top_errors[:3]),
        ),
        EvidenceItem(source="metrics", summary=f"p95={latency.p95_ms}ms p99={latency.p99_ms}ms"),
        EvidenceItem(
            source="metrics",
            summary=f"latency anomaly={anomaly.is_anomaly} "
            f"(actual {anomaly.actual} vs [{anomaly.lower}, {anomaly.upper}])",
        ),
        EvidenceItem(
            source="deploys",
            summary=f"{len(deploys)} deploys in last 24h",
            detail="; ".join(f"{d.message} ({d.status})" for d in deploys[:3]),
        ),
    ]


def _deeper_round(service: str) -> list[EvidenceItem]:
    errors = find_error_traces(service, 360)
    slow = find_slow_traces(service, 500, 360)
    recent = get_recent_errors(service, 5)
    return [
        EvidenceItem(
            source="traces",
            summary=f"{len(errors)} error traces, {len(slow)} slow traces (last 6h)",
            detail="slowest: " + ", ".join(f"{t.duration_ms}ms" for t in slow[:3]),
        ),
        EvidenceItem(
            source="logs",
            summary="recent error messages",
            detail="; ".join(e.message for e in recent),
        ),
    ]


def investigate(state: GraphState) -> dict[str, object]:
    service = str(state["alert"].get("service", "unknown"))
    round_number = state.get("investigator_rounds", 0) + 1
    items = _first_round(service) if round_number == 1 else _deeper_round(service)
    log.info("node.investigator", service=service, round=round_number, gathered=len(items))
    return {"evidence": items, "investigator_rounds": round_number}
