"""Hypothesizer — proposes a structured, ranked list of likely root causes."""

from __future__ import annotations

import json

import structlog
from pydantic import BaseModel

from packages.agents.llm import structured
from packages.agents.state import GraphState, HypothesisItem

log = structlog.get_logger()

_SYSTEM = """[HYPOTHESES] You are the analysis member of an incident response team.
Given an alert and gathered evidence, propose 3-5 likely root causes, most likely
first. Reply with JSON only:
{"hypotheses": [{"statement": "...", "description": "...", "confidence": 0.0-1.0, "rank": 1}]}
rank starts at 1 (most likely). confidence is your 0-1 certainty."""


class _Hypotheses(BaseModel):
    hypotheses: list[HypothesisItem]


async def hypothesize(state: GraphState) -> dict[str, object]:
    alert = state["alert"]
    evidence = state.get("evidence", [])
    evidence_text = "\n".join(
        f"- [{e.source}] {e.summary}" + (f" ({e.detail})" if e.detail else "") for e in evidence
    )
    result = await structured(
        _SYSTEM,
        f"Alert: {json.dumps(alert)}\n\nEvidence:\n{evidence_text}",
        _Hypotheses,
    )
    hypotheses = result.hypotheses[:5]
    log.info("node.hypothesizer", count=len(hypotheses))
    return {"hypotheses": hypotheses}
