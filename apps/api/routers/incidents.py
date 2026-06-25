"""Read endpoints for incidents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from packages.core.repositories import IncidentRepository, ServiceRepository
from packages.core.schemas import IncidentRead

from apps.api.deps import SessionDep

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("")
async def recent_incidents(
    session: SessionDep, service: str | None = None, last_n_hours: int = 24
) -> list[IncidentRead]:
    """Recent incidents, optionally filtered by service (newest first)."""
    service_id = None
    if service:
        found = await ServiceRepository(session).get_by_name(service)
        service_id = found.id if found is not None else None

    since = datetime.now(UTC) - timedelta(hours=last_n_hours)
    incidents = await IncidentRepository(session).list_recent(since, service_id=service_id)
    return [IncidentRead.model_validate(i) for i in incidents]
