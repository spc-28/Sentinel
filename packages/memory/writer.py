"""Save solved incidents to memory and update memory weights from human feedback."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config import get_settings
from packages.core.models import PastIncident
from packages.core.repositories import PastIncidentRepository
from packages.memory.fingerprint import fingerprint, signature_from_alert
from packages.memory.similarity import embed_text, text_similarity

log = structlog.get_logger()


async def remember(
    session: AsyncSession,
    *,
    alert: dict[str, object],
    root_cause: str,
    recommended_fix: str | None = None,
    investigation_id: UUID | None = None,
) -> PastIncident:
    """Store (or refresh) the memory for a solved incident.

    Re-seeing the same fingerprint bumps its occurrence count and refreshes the
    cause/fix rather than creating a duplicate.
    """
    signature = signature_from_alert(alert)
    fp = fingerprint(signature)
    repo = PastIncidentRepository(session)
    embedding = embed_text(signature.text)

    existing = await repo.get_by_fingerprint(fp)
    if existing is not None:
        existing.occurrences += 1
        existing.root_cause = root_cause
        existing.recommended_fix = recommended_fix
        existing.last_seen_at = datetime.now(UTC)
        if embedding is not None:
            existing.embedding = embedding
        if investigation_id is not None:
            existing.investigation_id = investigation_id
        await session.flush()
        await session.refresh(existing)
        log.info("memory.updated", fingerprint=fp, occurrences=existing.occurrences)
        return existing

    created = await repo.create(
        service=signature.service,
        alert_type=signature.alert_type,
        main_error=signature.main_error,
        fingerprint=fp,
        signature_text=signature.text,
        title=signature.alert_type,
        root_cause=root_cause,
        recommended_fix=recommended_fix,
        investigation_id=investigation_id,
        embedding=embedding,
        weight=get_settings().memory_default_weight,
        last_seen_at=datetime.now(UTC),
    )
    log.info("memory.saved", fingerprint=fp, service=signature.service)
    return created


async def record_confirmation(
    session: AsyncSession, investigation_id: UUID, confirmed_cause: str
) -> PastIncident | None:
    """Record a human-confirmed cause and re-weight the memory by how well the
    saved report matched it. A close match keeps the memory trusted; a poor match
    demotes it so future recalls re-investigate instead of trusting a wrong cause.
    """
    repo = PastIncidentRepository(session)
    incident = await repo.get_by_investigation(investigation_id)
    if incident is None:
        return None

    match = round(text_similarity(incident.root_cause, confirmed_cause), 4)
    incident.confirmed_cause = confirmed_cause
    incident.match_score = match
    # EMA toward the observed match quality — accumulates across confirmations.
    incident.weight = round(0.5 * incident.weight + 0.5 * match, 4)
    await session.flush()
    await session.refresh(incident)
    log.info(
        "memory.confirmed",
        past_incident_id=str(incident.id),
        match_score=match,
        weight=incident.weight,
    )
    return incident
