"""Reporter — fills a structured markdown report (root cause, timeline, evidence, fix)."""

from __future__ import annotations

import json

import structlog
from pydantic import BaseModel

from packages.agents.llm import structured
from packages.agents.state import EvidenceItem, GraphState, ReportDoc, VerifiedHypothesis

log = structlog.get_logger()

_SYSTEM = """[REPORT] You are the scribe of an incident response team. Given the
leading hypothesis and the evidence, write a concise root cause and a concrete
suggested fix. Reply with JSON only:
{"root_cause": "...", "suggested_fix": "..."}"""


class _ReportFields(BaseModel):
    root_cause: str
    suggested_fix: str


def _timeline(evidence: list[EvidenceItem]) -> list[str]:
    return [f"[{e.source}] {e.summary}" for e in evidence]


def _render(
    *, root_cause: str, timeline: list[str], evidence: list[str], suggested_fix: str
) -> str:
    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- (none)"

    return (
        f"## Root Cause\n{root_cause}\n\n"
        f"## Timeline\n{bullets(timeline)}\n\n"
        f"## Evidence\n{bullets(evidence)}\n\n"
        f"## Suggested Fix\n{suggested_fix}\n"
    )


def _false_alarm(state: GraphState) -> ReportDoc:
    note = state.get("detector_notes", "No anomalous signals found.")
    evidence = [e.summary for e in state.get("evidence", [])]
    return ReportDoc(
        root_cause="No incident — classified as a false alarm.",
        timeline=[],
        evidence=evidence,
        suggested_fix="No action needed. Consider tuning the alert threshold.",
        markdown=_render(
            root_cause=f"No incident — likely false alarm. {note}",
            timeline=[],
            evidence=evidence,
            suggested_fix="No action needed. Consider tuning the alert threshold.",
        ),
    )


async def report(state: GraphState) -> dict[str, object]:
    if not state.get("is_real", True):
        log.info("node.reporter", outcome="false_alarm")
        return {"report": _false_alarm(state)}

    evidence = state.get("evidence", [])
    verified: list[VerifiedHypothesis] = state.get("verified", [])
    leading = verified[0] if verified else None
    leading_text = (
        f"{leading.statement} (support {leading.support_score}, {leading.verdict})"
        if leading
        else "No strong hypothesis."
    )

    fields = await structured(
        _SYSTEM,
        f"Alert: {json.dumps(state['alert'])}\nLeading hypothesis: {leading_text}\n"
        + "Evidence:\n"
        + "\n".join(f"- [{e.source}] {e.summary}" for e in evidence),
        _ReportFields,
    )

    timeline = _timeline(evidence)
    evidence_lines = [f"[{e.source}] {e.summary}" for e in evidence]
    markdown = _render(
        root_cause=fields.root_cause,
        timeline=timeline,
        evidence=evidence_lines,
        suggested_fix=fields.suggested_fix,
    )
    log.info("node.reporter", outcome="report", has_leading=leading is not None)
    return {
        "report": ReportDoc(
            root_cause=fields.root_cause,
            timeline=timeline,
            evidence=evidence_lines,
            suggested_fix=fields.suggested_fix,
            markdown=markdown,
        )
    }
