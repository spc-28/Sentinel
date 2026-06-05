"""Inbound webhooks. Currently: alert ingestion."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, status
from packages.core.repositories import AlertRepository, ServiceRepository
from packages.core.schemas import AlertWebhook

from apps.api.deps import QueueDep, SessionDep

log = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

INVESTIGATE_ALERT_JOB = "investigate_alert"


@router.post("/alert", status_code=status.HTTP_202_ACCEPTED)
async def receive_alert(
    payload: AlertWebhook, session: SessionDep, queue: QueueDep
) -> dict[str, str]:
    """Persist an incoming alert and queue it for investigation."""
    service_id = None
    if payload.service:
        service = await ServiceRepository(session).get_by_name(payload.service)
        service_id = service.id if service is not None else None

    alert = await AlertRepository(session).create(
        service_id=service_id,
        title=payload.title,
        severity=payload.severity,
        source=payload.source,
        fingerprint=payload.fingerprint,
        payload=payload.payload,
        triggered_at=payload.triggered_at,
    )
    # Commit before enqueuing so the worker never sees an alert id that isn't persisted.
    await session.commit()

    job_id = await queue.enqueue(INVESTIGATE_ALERT_JOB, {"alert_id": str(alert.id)})
    log.info("webhook.alert_received", alert_id=str(alert.id), job_id=job_id)

    return {"status": "accepted", "alert_id": str(alert.id), "job_id": job_id}
