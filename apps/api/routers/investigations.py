"""Read endpoints for investigations."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from packages.core.repositories import HypothesisRepository, InvestigationRepository
from packages.core.schemas import HypothesisRead, InvestigationDetail, InvestigationRead

from apps.api.deps import SessionDep

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: UUID, session: SessionDep) -> InvestigationDetail:
    """Return an investigation with its ranked hypotheses."""
    investigation = await InvestigationRepository(session).get(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="investigation not found")

    hypotheses = await HypothesisRepository(session).list_for_investigation(investigation_id)
    return InvestigationDetail(
        investigation=InvestigationRead.model_validate(investigation),
        hypotheses=[HypothesisRead.model_validate(h) for h in hypotheses],
    )
