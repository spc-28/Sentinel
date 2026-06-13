"""Investigate-alert job: run the agent and persist Investigation + Hypothesis rows."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import structlog
from packages.agents.simple_agent import run_investigation
from packages.core.db import session_factory
from packages.core.enums import InvestigationStatus
from packages.core.repositories import (
    AlertRepository,
    HypothesisRepository,
    IncidentRepository,
    InvestigationRepository,
    ServiceRepository,
)

log = structlog.get_logger()


async def handle_investigate(alert_id: str) -> None:
    """Create an incident + investigation for the alert, run the agent, save results."""
    # 1. Load the alert and open an investigation.
    async with session_factory() as session:
        alert = await AlertRepository(session).get(UUID(alert_id))
        if alert is None:
            log.warning("investigate.alert_not_found", alert_id=alert_id)
            return

        service_name = "unknown"
        if alert.service_id is not None:
            service = await ServiceRepository(session).get(alert.service_id)
            if service is not None:
                service_name = service.name

        incident = await IncidentRepository(session).create(
            alert_id=alert.id, service_id=alert.service_id, title=alert.title
        )
        investigation = await InvestigationRepository(session).create(
            incident_id=incident.id,
            status=InvestigationStatus.running,
            started_at=datetime.now(UTC),
        )
        # Capture primitives before the session closes.
        investigation_id = investigation.id
        title, severity, payload = alert.title, alert.severity.value, dict(alert.payload)
        await session.commit()

    log.info("investigate.started", investigation_id=str(investigation_id), service=service_name)

    # 2. Run the agent (sync/blocking) off the event loop.
    try:
        result = await asyncio.to_thread(run_investigation, service_name, title, severity, payload)
    except Exception as exc:  # noqa: BLE001 - record failure, don't crash the worker
        log.error("investigate.failed", investigation_id=str(investigation_id), error=str(exc))
        async with session_factory() as session:
            await InvestigationRepository(session).update(
                investigation_id,
                status=InvestigationStatus.failed,
                completed_at=datetime.now(UTC),
                error=str(exc),
            )
            await session.commit()
        return

    # 3. Persist hypotheses and mark the investigation complete.
    async with session_factory() as session:
        hypotheses = HypothesisRepository(session)
        for draft in result.hypotheses[:3]:
            await hypotheses.create(
                investigation_id=investigation_id,
                statement=draft.statement,
                description=draft.description,
                confidence=draft.confidence,
                rank=draft.rank,
            )
        await InvestigationRepository(session).update(
            investigation_id,
            status=InvestigationStatus.completed,
            completed_at=datetime.now(UTC),
        )
        await session.commit()

    log.info(
        "investigate.completed",
        investigation_id=str(investigation_id),
        steps=result.steps_used,
        hypotheses=len(result.hypotheses),
    )
