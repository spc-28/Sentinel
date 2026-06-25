"""Read endpoints for investigations."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from packages.core.repositories import (
    AlertRepository,
    HypothesisRepository,
    IncidentRepository,
    InvestigationRepository,
    RCAReportRepository,
    ServiceRepository,
)
from packages.core.schemas import (
    ConfirmCause,
    HypothesisRead,
    InvestigationDetail,
    InvestigationRead,
    PastIncidentRead,
    RCAReportRead,
    SuggestFix,
)
from packages.memory.writer import record_confirmation
from packages.tools.deploys import draft_revert, recent_deploys

from apps.api.deps import SessionDep

router = APIRouter(prefix="/investigations", tags=["investigations"])


async def _detail(session: SessionDep, investigation_id: UUID) -> InvestigationDetail:
    investigation = await InvestigationRepository(session).get(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="investigation not found")
    hypotheses = await HypothesisRepository(session).list_for_investigation(investigation_id)
    rca = await RCAReportRepository(session).get_for_investigation(investigation_id)
    return InvestigationDetail(
        investigation=InvestigationRead.model_validate(investigation),
        hypotheses=[HypothesisRead.model_validate(h) for h in hypotheses],
        report=RCAReportRead.model_validate(rca) if rca is not None else None,
    )


# Static paths must precede /{investigation_id} so they aren't parsed as an id.
@router.get("/search")
async def search_past_incidents(session: SessionDep, q: str) -> list[RCAReportRead]:
    """Search past RCA reports (root cause / summary / fix) for relevant history."""
    reports = await RCAReportRepository(session).search(q)
    return [RCAReportRead.model_validate(r) for r in reports]


@router.get("/by-alert/{alert_id}")
async def get_investigation_by_alert(alert_id: UUID, session: SessionDep) -> InvestigationDetail:
    """Find the investigation opened for a given alert (via its incident)."""
    incident = await IncidentRepository(session).get_by_alert(alert_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no incident for alert")
    investigation = await InvestigationRepository(session).get_by_incident(incident.id)
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no investigation yet")
    return await _detail(session, investigation.id)


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: UUID, session: SessionDep) -> InvestigationDetail:
    """Return an investigation with its ranked hypotheses."""
    return await _detail(session, investigation_id)


@router.get("/{investigation_id}/suggest-fix")
async def suggest_fix(investigation_id: UUID, session: SessionDep) -> SuggestFix:
    """Propose a fix (from the report) plus a draft revert PR for the latest deploy."""
    investigation = await InvestigationRepository(session).get(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="investigation not found")

    incident = await IncidentRepository(session).get(investigation.incident_id)
    service_name = "unknown"
    if incident is not None:
        alert = await AlertRepository(session).get(incident.alert_id)
        if alert is not None and alert.service_id is not None:
            service = await ServiceRepository(session).get(alert.service_id)
            service_name = service.name if service is not None else "unknown"

    rca = await RCAReportRepository(session).get_for_investigation(investigation_id)

    revert_url = None
    revert_title = None
    deploys = recent_deploys(service_name, 1440)
    if deploys:
        revert = draft_revert(deploys[0].deploy_id)
        revert_url = revert.revert_pr_url
        revert_title = revert.title

    return SuggestFix(
        investigation_id=investigation_id,
        root_cause=rca.root_cause if rca is not None else None,
        recommended_fix=rca.recommended_fix if rca is not None else None,
        revert_pr_url=revert_url,
        revert_title=revert_title,
        note="Suggested fix from the RCA report; the revert PR is a draft only.",
    )


@router.post("/{investigation_id}/confirm-cause")
async def confirm_cause(
    investigation_id: UUID, body: ConfirmCause, session: SessionDep
) -> PastIncidentRead:
    """Record the human-confirmed cause, re-weighting the remembered incident by how
    well its saved report matched (well-matched memories are trusted more on recall)."""
    incident = await record_confirmation(session, investigation_id, body.cause)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no remembered incident for investigation"
        )
    return PastIncidentRead.model_validate(incident)
