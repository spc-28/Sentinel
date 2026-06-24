"""Hypothesizer — proposes a structured, ranked list of likely root causes."""

from __future__ import annotations

import json

import structlog
from pydantic import BaseModel

from packages.agents.llm import structured
from packages.agents.state import GraphState, HypothesisItem
from packages.graph.store import blast_radius, dependents

log = structlog.get_logger()

_SYSTEM = """[HYPOTHESES] You are the analysis member of an incident response team.
Given an alert, gathered evidence, and the service dependency context, propose 3-5
likely root causes, most likely first. Use the dependency context to reason about
knock-on effects: the services the alerting service depends on are candidate
culprits, and services that depend on it should also show symptoms if it is the
cause. Reply with JSON only:
{"hypotheses": [{"statement": "...", "description": "...", "confidence": 0.0-1.0, "rank": 1}]}
rank starts at 1 (most likely). confidence is your 0-1 certainty."""


class _Hypotheses(BaseModel):
    hypotheses: list[HypothesisItem]


async def _dependency_context(service: str) -> str:
    try:
        downstream = await blast_radius(service, 2)
        upstream = await dependents(service, 2)
    except Exception as exc:  # noqa: BLE001 - graph optional
        log.warning("hypothesizer.graph_unavailable", error=str(exc))
        return "Dependency map unavailable."
    return (
        f"{service} depends on: {', '.join(downstream) or 'nothing known'}.\n"
        f"Services that depend on {service}: {', '.join(upstream) or 'none known'}."
    )


async def hypothesize(state: GraphState) -> dict[str, object]:
    alert = state["alert"]
    evidence = state.get("evidence", [])
    evidence_text = "\n".join(
        f"- [{e.source}] {e.summary}" + (f" ({e.detail})" if e.detail else "") for e in evidence
    )
    from packages.agents.ai_pipeline import is_ai_alert

    context = await _dependency_context(str(alert.get("service", "unknown")))
    ai_hint = ""
    if is_ai_alert(alert):
        ai_hint = (
            "\n\nThis is an AI-pipeline alert. Consider AI-specific causes: an embedding "
            "model changed and the index wasn't rebuilt (drift); a new prompt version shipped "
            "with a regression; RAG retrieval quality dropped; or an AI cost spike."
        )
    result = await structured(
        _SYSTEM,
        f"Alert: {json.dumps(alert)}\n\nDependency context:\n{context}{ai_hint}\n\n"
        f"Evidence:\n{evidence_text}",
        _Hypotheses,
    )
    hypotheses = result.hypotheses[:5]
    log.info("node.hypothesizer", count=len(hypotheses))
    return {"hypotheses": hypotheses}
