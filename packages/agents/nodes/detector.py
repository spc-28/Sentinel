"""Detector — decides whether the alert is a real incident or a false alarm."""

from __future__ import annotations

import json

import structlog
from pydantic import BaseModel

from packages.agents.llm import structured
from packages.agents.state import EvidenceItem, GraphState
from packages.tools.logs import summarize_logs
from packages.tools.metrics import is_anomaly

log = structlog.get_logger()

_SYSTEM = """[DETECTOR] You are the triage member of an incident response team.
Given an alert and a few quick signals, decide if this is a REAL incident worth
investigating, or a likely false alarm. Reply with JSON only:
{"is_real": true|false, "reason": "one sentence"}"""


class _Verdict(BaseModel):
    is_real: bool
    reason: str


def _is_incident(alert: dict[str, object]) -> bool:
    """A critical/high alert (or an explicit ``incident`` payload flag) is a real
    incident: its signals come back degraded. Lower severities are triaged by the
    LLM against baseline signals, and usually filtered out as false alarms."""
    severity = str(alert.get("severity", "")).lower()
    if severity in ("critical", "high"):
        return True
    details = alert.get("details")
    return isinstance(details, dict) and bool(details.get("incident"))


async def detect(state: GraphState) -> dict[str, object]:
    alert = state["alert"]
    service = str(alert.get("service", "unknown"))
    incident = _is_incident(alert)

    summary = summarize_logs(service, 60, incident=incident)
    anomaly = is_anomaly(service, "latency_ms", 30, incident=incident)
    signals = (
        f"error_rate={summary.error_rate}, error_logs={summary.by_level.get('ERROR', 0)}, "
        f"latency_anomaly={anomaly.is_anomaly} (actual {anomaly.actual} vs "
        f"[{anomaly.lower}, {anomaly.upper}])"
    )

    if incident:
        verdict = _Verdict(
            is_real=True,
            reason="High-severity alert with an elevated error rate and latency anomaly.",
        )
    else:
        verdict = await structured(
            _SYSTEM, f"Alert: {json.dumps(alert)}\nSignals: {signals}", _Verdict
        )
    log.info("node.detector", service=service, is_real=verdict.is_real, incident=incident)
    return {
        "is_real": verdict.is_real,
        "incident": incident,
        "detector_notes": verdict.reason,
        "evidence": [EvidenceItem(source="metrics", summary=f"triage signals — {signals}")],
    }
