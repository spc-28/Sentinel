"""Turn past investigations into QLoRA training examples (alert + evidence → cause).

Reads solved incidents (RCAReport → Investigation → Incident → Alert) and writes
chat-format JSONL to experiments/finetune/data/. If there are too few real reports,
it can bootstrap with Claude-generated synthetic examples (needs ANTHROPIC_API_KEY).

    make training-data                 # real reports only
    make training-data SYNTHETIC=30    # top up to 30 total with synthetic examples
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import structlog
from packages.core.db import session_factory
from packages.core.logging import configure_logging
from packages.core.repositories import (
    AlertRepository,
    IncidentRepository,
    InvestigationRepository,
    RCAReportRepository,
    ServiceRepository,
)

log = structlog.get_logger()

_OUT_DIR = Path(__file__).resolve().parent.parent / "experiments" / "finetune" / "data"
_SYSTEM = (
    "You are a site-reliability engineer. Given an alert and gathered evidence, "
    "state the most likely root cause and a concrete suggested fix."
)


def _example(user: str, assistant: str) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def _user_prompt(alert_title: str, service: str, severity: str, evidence: list[str]) -> str:
    lines = "\n".join(f"- {e}" for e in evidence) or "- (none captured)"
    return f"Alert: {alert_title} on {service} (severity {severity}).\nEvidence:\n{lines}"


def _assistant_answer(root_cause: str, fix: str | None) -> str:
    return f"Root cause: {root_cause}\nSuggested fix: {fix or 'N/A'}"


async def _from_reports() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    async with session_factory() as session:
        reports = await RCAReportRepository(session).list(limit=1000)
        for rca in reports:
            investigation = await InvestigationRepository(session).get(rca.investigation_id)
            if investigation is None:
                continue
            incident = await IncidentRepository(session).get(investigation.incident_id)
            if incident is None:
                continue
            alert = await AlertRepository(session).get(incident.alert_id)
            if alert is None:
                continue
            service = "unknown"
            if alert.service_id is not None:
                svc = await ServiceRepository(session).get(alert.service_id)
                service = svc.name if svc is not None else "unknown"
            evidence = [str(item.get("event", "")) for item in rca.timeline]
            examples.append(
                _example(
                    _user_prompt(alert.title, service, alert.severity.value, evidence),
                    _assistant_answer(rca.root_cause, rca.recommended_fix),
                )
            )
    return examples


async def _synthetic(count: int) -> list[dict[str, Any]]:
    """Generate synthetic (alert + evidence → cause) examples with Claude."""
    if not os.environ.get("ANTHROPIC_API_KEY") and not _has_key():
        log.warning("training_data.synthetic_skipped", reason="no ANTHROPIC_API_KEY")
        return []
    from packages.agents.llm import structured
    from pydantic import BaseModel

    class _Case(BaseModel):
        alert_title: str
        service: str
        severity: str
        evidence: list[str]
        root_cause: str
        suggested_fix: str

    class _Cases(BaseModel):
        cases: list[_Case]

    system = (
        "[SYNTHETIC] Generate realistic SRE incident training cases for services like "
        "checkout-api, auth-service, search-api, inventory-service, notifications-worker. "
        "Vary the failure type (DB pool, bad deploy, cache, timeouts, disk, auth). "
        'Reply with JSON only: {"cases": [{"alert_title","service","severity",'
        '"evidence":[...],"root_cause","suggested_fix"}]}'
    )
    result = await structured(system, f"Produce {count} diverse cases.", _Cases)
    return [
        _example(
            _user_prompt(c.alert_title, c.service, c.severity, c.evidence),
            _assistant_answer(c.root_cause, c.suggested_fix),
        )
        for c in result.cases[:count]
    ]


def _has_key() -> bool:
    from packages.core.config import get_settings

    return bool(get_settings().anthropic_api_key)


def _write(examples: list[dict[str, Any]]) -> None:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    split = max(1, int(len(examples) * 0.9)) if len(examples) > 1 else len(examples)
    for name, rows in (("train", examples[:split]), ("val", examples[split:])):
        path = _OUT_DIR / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        log.info("training_data.written", file=str(path), rows=len(rows))


async def main() -> None:
    configure_logging()
    target_synthetic = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    examples = await _from_reports()
    log.info("training_data.from_reports", count=len(examples))
    if len(examples) < target_synthetic:
        examples += await _synthetic(target_synthetic - len(examples))

    _write(examples)
    log.info("training_data.done", total=len(examples))


if __name__ == "__main__":
    asyncio.run(main())
