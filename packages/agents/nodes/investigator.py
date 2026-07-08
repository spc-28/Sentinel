"""Investigator — gathers evidence from the Part 3 tools.

Deterministic on purpose: round 1 collects the headline signals; later rounds
(triggered by the verifier retry loop) dig deeper into traces and recent errors.

Before investigating, it checks memory (Part 11). On a strong match to a past
incident it starts from the known cause and only gathers enough to confirm it —
far fewer tool calls than a cold investigation, so a repeat incident is solved
faster the second time.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from packages.agents.observability import tool_span
from packages.agents.state import EvidenceItem, GraphState
from packages.memory.recall import Recollection, recall_for_alert
from packages.tools.deploys import recent_deploys
from packages.tools.logs import get_recent_errors, summarize_logs
from packages.tools.metrics import get_p95_latency, is_anomaly
from packages.tools.traces import find_error_traces, find_slow_traces

log = structlog.get_logger()


class _Meter:
    """Routes every tool call through one counter, so a memory-guided run can be
    shown to touch fewer tools than a cold investigation. Each call is also a
    Langfuse span, so the trace shows the exact tools an investigation used."""

    def __init__(self) -> None:
        self.calls = 0

    def run[T](self, fn: Callable[..., T], *args: object) -> T:
        self.calls += 1
        with tool_span(f"tool:{fn.__name__}"):
            return fn(*args)

    async def arun[T](self, fn: Callable[..., Awaitable[T]], *args: object, **kwargs: object) -> T:
        self.calls += 1
        with tool_span(f"tool:{fn.__name__}"):
            return await fn(*args, **kwargs)


def _first_round(service: str, meter: _Meter, incident: bool = False) -> list[EvidenceItem]:
    summary = meter.run(summarize_logs, service, 60, incident)
    latency = meter.run(get_p95_latency, service, 60, incident)
    anomaly = meter.run(is_anomaly, service, "latency_ms", 30, incident)
    deploys = meter.run(recent_deploys, service, 1440)
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


def _deeper_round(service: str, meter: _Meter, incident: bool = False) -> list[EvidenceItem]:
    errors = meter.run(find_error_traces, service, 360)
    slow = meter.run(find_slow_traces, service, 500, 360)
    recent = meter.run(get_recent_errors, service, 5, incident)
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


def _memory_confirm_round(
    service: str, recall: Recollection, meter: _Meter, incident: bool = False
) -> list[EvidenceItem]:
    """Memory hit: lead with the recalled cause, then gather just enough to confirm."""
    deploys = meter.run(recent_deploys, service, 1440)
    anomaly = meter.run(is_anomaly, service, "latency_ms", 30, incident)
    fix = f" Prior fix: {recall.recommended_fix}" if recall.recommended_fix else ""
    return [
        EvidenceItem(
            source="memory",
            summary=f"Known root cause from {recall.occurrences} past incident(s): "
            f"{recall.root_cause}",
            detail=f"recall score {recall.score} (weight {recall.weight}).{fix}",
        ),
        EvidenceItem(
            source="deploys",
            summary=f"{len(deploys)} deploys in last 24h",
            detail="; ".join(f"{d.message} ({d.status})" for d in deploys[:3]),
        ),
        EvidenceItem(
            source="metrics",
            summary=f"latency anomaly={anomaly.is_anomaly} (actual {anomaly.actual})",
        ),
    ]


async def _rag_evidence(query: str, meter: _Meter) -> list[EvidenceItem]:
    """Search runbooks and similar past logs for relevant context (best effort)."""
    items: list[EvidenceItem] = []
    try:
        from packages.rag.retriever import search_logs, search_runbooks

        for hit in await meter.arun(search_runbooks, query, top_k=2):
            items.append(
                EvidenceItem(source="runbook", summary=f"runbook: {hit.title}", detail=hit.content)
            )
        similar = await meter.arun(search_logs, query, top_k=3)
        if similar:
            items.append(
                EvidenceItem(
                    source="logs",
                    summary="similar past logs",
                    detail="; ".join(f"[{h.service}] {h.message}" for h in similar),
                )
            )
    except Exception as exc:  # noqa: BLE001 - RAG optional
        log.warning("investigator.rag_unavailable", error=str(exc))
    return items


async def _ai_evidence(alert: dict[str, object], service: str, meter: _Meter) -> list[EvidenceItem]:
    """Specialist branch for AI-type alerts: vector health, prompt/model versions, cost."""
    from packages.agents.ai_pipeline.detectors import (
        check_embedding_drift,
        check_prompt_regression,
        check_rag_quality,
        get_ai_cost,
    )

    details = alert.get("details", {})
    index = details.get("index", "runbooks") if isinstance(details, dict) else "runbooks"
    try:
        drift = await meter.arun(check_embedding_drift, str(index))
        quality = await meter.arun(check_rag_quality, str(index))
        prompt = await meter.arun(check_prompt_regression, service)
        cost = await meter.arun(get_ai_cost, service)
    except Exception as exc:  # noqa: BLE001 - detectors optional
        log.warning("investigator.ai_detectors_unavailable", error=str(exc))
        return []
    return [
        EvidenceItem(
            source="ai_pipeline",
            summary=f"embedding drift: {drift.drift_detected}",
            detail=f"wasserstein {drift.wasserstein} (>{drift.threshold}?) — {drift.note}",
        ),
        EvidenceItem(
            source="ai_pipeline",
            summary=f"RAG faithfulness: {quality.faithfulness}",
            detail=quality.note,
        ),
        EvidenceItem(
            source="ai_pipeline",
            summary=f"prompt regression: {prompt.regressed}",
            detail=prompt.note,
        ),
        EvidenceItem(
            source="ai_pipeline", summary=f"AI cost spike: {cost.spike_detected}", detail=cost.note
        ),
    ]


async def investigate(state: GraphState) -> dict[str, object]:
    from packages.agents.ai_pipeline import is_ai_alert

    alert = state["alert"]
    service = str(alert.get("service", "unknown"))
    incident = bool(state.get("incident", False))
    round_number = state.get("investigator_rounds", 0) + 1
    meter = _Meter()

    if round_number == 1:
        recollections = await recall_for_alert(alert)
        top = recollections[0] if recollections else None
        if top is not None and top.is_strong:
            items = _memory_confirm_round(service, top, meter, incident)
            log.info(
                "node.investigator",
                service=service,
                round=round_number,
                gathered=len(items),
                tool_calls=meter.calls,
                memory_hit=True,
                recall_score=top.score,
            )
            return {
                "evidence": items,
                "investigator_rounds": round_number,
                "tool_calls": meter.calls,
                "memory_hit": True,
                "known_cause": top.root_cause,
            }

    items = (
        _first_round(service, meter, incident)
        if round_number == 1
        else _deeper_round(service, meter, incident)
    )
    if round_number == 1:
        items.extend(await _rag_evidence(f"{alert.get('title', '')} {service}", meter))
        if is_ai_alert(alert):
            items.extend(await _ai_evidence(alert, service, meter))
    log.info(
        "node.investigator",
        service=service,
        round=round_number,
        gathered=len(items),
        tool_calls=meter.calls,
        memory_hit=False,
    )
    return {
        "evidence": items,
        "investigator_rounds": round_number,
        "tool_calls": meter.calls,
    }
