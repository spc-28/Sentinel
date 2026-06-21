"""Read endpoints for incident groups (correlated alerts)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from packages.core.repositories import AlertRepository, IncidentGroupRepository
from packages.core.schemas import AlertRead, IncidentGroupDetail, IncidentGroupRead

from apps.api.deps import SessionDep

router = APIRouter(prefix="/incident-groups", tags=["incident-groups"])


@router.get("")
async def list_groups(session: SessionDep) -> list[IncidentGroupRead]:
    """List recent incident groups (newest first)."""
    groups = await IncidentGroupRepository(session).list(limit=50)
    return [IncidentGroupRead.model_validate(g) for g in groups]


@router.get("/{group_id}")
async def get_group(group_id: UUID, session: SessionDep) -> IncidentGroupDetail:
    """An incident group with its member alerts."""
    group = await IncidentGroupRepository(session).get(group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group not found")
    alerts = await AlertRepository(session).list_for_group(group_id)
    return IncidentGroupDetail(
        group=IncidentGroupRead.model_validate(group),
        alerts=[AlertRead.model_validate(a) for a in alerts],
    )
