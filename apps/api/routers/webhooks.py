"""Inbound webhooks. Currently: alert ingestion with correlation/grouping."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, status
from packages.agents.correlation import severity_rank
from packages.agents.correlation.combiner import correlate
from packages.agents.correlation.types import AlertView, GroupView
from packages.core.config import get_settings
from packages.core.enums import GroupStatus
from packages.core.repositories import (
    AlertRepository,
    IncidentGroupRepository,
    ServiceRepository,
)
from packages.core.schemas import AlertWebhook

from apps.api.deps import QueueDep, SessionDep

log = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

INVESTIGATE_ALERT_JOB = "investigate_alert"


async def _group_views(session: SessionDep, groups: list[Any]) -> list[GroupView]:
    """Build correlation views, resolving each group's service name."""
    service_repo = ServiceRepository(session)
    names: dict[Any, str] = {}
    for service_id in {g.service_id for g in groups if g.service_id is not None}:
        service = await service_repo.get(service_id)
        if service is not None:
            names[service_id] = service.name
    return [
        GroupView(
            id=g.id,
            service=names.get(g.service_id),
            title=g.title,
            leader_severity=g.severity,
            last_activity=g.last_activity_at,
        )
        for g in groups
    ]


@router.post("/alert", status_code=status.HTTP_202_ACCEPTED)
async def receive_alert(
    payload: AlertWebhook, session: SessionDep, queue: QueueDep
) -> dict[str, Any]:
    """Persist an alert, correlate it into a group, and queue work only for new groups."""
    settings = get_settings()
    service_name = payload.service or "unknown"
    service_id = None
    if payload.service:
        service = await ServiceRepository(session).get_by_name(payload.service)
        service_id = service.id if service is not None else None

    triggered = payload.triggered_at or datetime.now(UTC)
    alert = await AlertRepository(session).create(
        service_id=service_id,
        title=payload.title,
        severity=payload.severity,
        source=payload.source,
        fingerprint=payload.fingerprint,
        payload=payload.payload,
        triggered_at=triggered,
    )

    groups_repo = IncidentGroupRepository(session)
    since = datetime.now(UTC) - timedelta(minutes=settings.correlation_window_minutes)
    open_groups = list(await groups_repo.list_open_since(since))
    alert_view = AlertView(
        id=alert.id,
        service=service_name,
        title=alert.title,
        severity=alert.severity,
        triggered_at=triggered,
    )
    decision = correlate(alert_view, await _group_views(session, open_groups), settings)

    if decision.matched_group_id is not None:
        group = await groups_repo.get(decision.matched_group_id)
        assert group is not None  # noqa: S101 - just fetched from the decision
        updates: dict[str, Any] = {
            "last_activity_at": max(group.last_activity_at, triggered),
            "alert_count": group.alert_count + 1,
        }
        if severity_rank(alert.severity) > severity_rank(group.severity):
            updates["severity"] = alert.severity
            updates["leader_alert_id"] = alert.id
        await groups_repo.update(group.id, **updates)
        await AlertRepository(session).update(alert.id, group_id=group.id)
        await session.commit()
        log.info(
            "webhook.alert_grouped",
            alert_id=str(alert.id),
            group_id=str(group.id),
            method=decision.method,
        )
        return {
            "status": "accepted",
            "alert_id": str(alert.id),
            "group_id": str(group.id),
            "grouped": True,
            "method": decision.method,
            "investigation_triggered": False,
        }

    group = await groups_repo.create(
        title=alert.title,
        service_id=service_id,
        severity=alert.severity,
        status=GroupStatus.open,
        leader_alert_id=alert.id,
        last_activity_at=triggered,
        alert_count=1,
    )
    await AlertRepository(session).update(alert.id, group_id=group.id)
    await session.commit()  # persist before enqueuing

    job_id = await queue.enqueue(INVESTIGATE_ALERT_JOB, {"alert_id": str(alert.id)})
    log.info("webhook.group_created", alert_id=str(alert.id), group_id=str(group.id), job_id=job_id)
    return {
        "status": "accepted",
        "alert_id": str(alert.id),
        "group_id": str(group.id),
        "grouped": False,
        "method": None,
        "investigation_triggered": True,
    }
