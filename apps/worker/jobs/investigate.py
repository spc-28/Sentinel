"""Investigate-alert job: run the five-agent graph and persist the results.

State is checkpointed in Postgres by the graph, so an investigation interrupted
by a worker crash can be resumed (see ``recover_running``).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from packages.agents.graph import run_graph
from packages.agents.state import GraphState, HypothesisItem, VerifiedHypothesis
from packages.core.db import session_factory
from packages.core.enums import InvestigationStatus
from packages.core.repositories import (
    AlertRepository,
    HypothesisRepository,
    IncidentRepository,
    InvestigationRepository,
    RCAReportRepository,
    ServiceRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


async def _service_name(session: AsyncSession, service_id: UUID | None) -> str:
    if service_id is None:
        return "unknown"
    service = await ServiceRepository(session).get(service_id)
    return service.name if service is not None else "unknown"


async def _alert_payload(session: AsyncSession, alert_id: UUID) -> dict[str, Any] | None:
    alert = await AlertRepository(session).get(alert_id)
    if alert is None:
        return None
    return {
        "service": await _service_name(session, alert.service_id),
        "title": alert.title,
        "severity": alert.severity.value,
        "details": dict(alert.payload),
    }


async def handle_investigate(alert_id: str) -> None:
    """Open an incident + investigation for the alert, then run the graph."""
    async with session_factory() as session:
        payload = await _alert_payload(session, UUID(alert_id))
        if payload is None:
            log.warning("investigate.alert_not_found", alert_id=alert_id)
            return
        incident = await IncidentRepository(session).create(
            alert_id=UUID(alert_id), title=payload["title"]
        )
        investigation = await InvestigationRepository(session).create(
            incident_id=incident.id,
            status=InvestigationStatus.running,
            started_at=datetime.now(UTC),
        )
        investigation_id = investigation.id
        await session.commit()

    log.info(
        "investigate.started", investigation_id=str(investigation_id), service=payload["service"]
    )
    await _run_and_persist(investigation_id, payload, resume=False)


async def resume_investigation(investigation_id: UUID) -> None:
    """Resume an interrupted investigation from its last checkpoint."""
    async with session_factory() as session:
        investigation = await InvestigationRepository(session).get(investigation_id)
        if investigation is None:
            return
        incident = await IncidentRepository(session).get(investigation.incident_id)
        payload = await _alert_payload(session, incident.alert_id) if incident is not None else None
    if payload is None:
        log.warning("investigate.resume_no_alert", investigation_id=str(investigation_id))
        return
    log.info("investigate.resuming", investigation_id=str(investigation_id))
    await _run_and_persist(investigation_id, payload, resume=True)


async def recover_running() -> None:
    """On startup, resume any investigations left in the 'running' state."""
    async with session_factory() as session:
        running_ids = [inv.id for inv in await InvestigationRepository(session).list_running()]
    for investigation_id in running_ids:
        try:
            await resume_investigation(investigation_id)
        except Exception as exc:  # noqa: BLE001 - keep recovering the rest
            log.error(
                "investigate.recover_failed", investigation_id=str(investigation_id), error=str(exc)
            )


async def _run_and_persist(
    investigation_id: UUID, payload: dict[str, Any], *, resume: bool
) -> None:
    try:
        final = await run_graph(payload, str(investigation_id), resume=resume)
    except Exception as exc:  # noqa: BLE001 - record failure, don't crash the worker
        if resume:  # no usable checkpoint → start a fresh run
            log.warning("investigate.resume_fresh", investigation_id=str(investigation_id))
            try:
                final = await run_graph(payload, str(investigation_id), resume=False)
            except Exception as exc2:  # noqa: BLE001
                await _mark_failed(investigation_id, str(exc2))
                return
        else:
            await _mark_failed(investigation_id, str(exc))
            return
    await _persist(investigation_id, final)


async def _mark_failed(investigation_id: UUID, error: str) -> None:
    log.error("investigate.failed", investigation_id=str(investigation_id), error=error)
    async with session_factory() as session:
        await InvestigationRepository(session).update(
            investigation_id,
            status=InvestigationStatus.failed,
            completed_at=datetime.now(UTC),
            error=error,
        )
        await session.commit()


async def _persist(investigation_id: UUID, final: GraphState) -> None:
    verified = final.get("verified") or []
    hypotheses: Sequence[HypothesisItem | VerifiedHypothesis] = (
        verified if verified else (final.get("hypotheses") or [])
    )
    report = final.get("report")

    async with session_factory() as session:
        hyp_repo = HypothesisRepository(session)
        for rank, hyp in enumerate(hypotheses[:3], start=1):  # DB allows rank 1..3
            await hyp_repo.create(
                investigation_id=investigation_id,
                statement=hyp.statement,
                description=hyp.description,
                confidence=hyp.confidence,
                rank=rank,
            )
        if report is not None:
            await RCAReportRepository(session).create(
                investigation_id=investigation_id,
                summary=report.markdown,  # full rendered report
                root_cause=report.root_cause,
                timeline=[{"event": item} for item in report.timeline],
                recommended_fix=report.suggested_fix,
            )
            await _remember(session, investigation_id, final, report)
        await InvestigationRepository(session).update(
            investigation_id,
            status=InvestigationStatus.completed,
            completed_at=datetime.now(UTC),
        )
        await session.commit()

    log.info(
        "investigate.completed",
        investigation_id=str(investigation_id),
        hypotheses=len(hypotheses[:3]),
        has_report=report is not None,
        tool_calls=final.get("tool_calls", 0),
        memory_hit=final.get("memory_hit", False),
    )


async def _remember(
    session: AsyncSession, investigation_id: UUID, final: GraphState, report: Any
) -> None:
    """Save each real incident to memory so the next similar one is solved faster.

    Runs alongside RCAReport persistence (both live here, not in the reporter node,
    which owns no DB session). False alarms are not remembered.
    """
    if not final.get("is_real", True):
        return
    try:
        from packages.memory.writer import remember

        await remember(
            session,
            alert=final.get("alert") or {},
            root_cause=report.root_cause,
            recommended_fix=report.suggested_fix,
            investigation_id=investigation_id,
        )
    except Exception as exc:  # noqa: BLE001 - memory optional, never fail the report
        log.warning("investigate.memory_save_failed", error=str(exc))
