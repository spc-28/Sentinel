"""Recall: given a new incident, find the most similar solved ones.

Two signals are combined per candidate:

- *fingerprint* — an exact structural match (service + alert type + main error) is
  strong evidence on its own.
- *meaning* — cosine similarity of the signature embeddings (lexical overlap if
  embeddings are unavailable).

Each candidate's similarity is scaled by its ``weight`` (how well its past reports
matched human-confirmed causes), so memories that proved accurate rank higher and
memories that proved wrong are distrusted. A recollection is *strong* when that
weighted score clears ``memory_strong_match_threshold`` — the investigator then
starts from the recalled cause instead of investigating from scratch.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config import get_settings
from packages.core.db import session_factory
from packages.core.models import PastIncident
from packages.core.repositories import PastIncidentRepository
from packages.memory.fingerprint import IncidentSignature, fingerprint, signature_from_alert
from packages.memory.similarity import cosine, embed_text, lexical

log = structlog.get_logger()

# An exact fingerprint match is near-certain even when embeddings are unavailable.
_EXACT_FP_SIMILARITY = 0.97
_CANDIDATE_POOL = 200


class Recollection(BaseModel):
    past_incident_id: UUID
    fingerprint: str
    service: str
    alert_type: str
    root_cause: str
    recommended_fix: str | None
    similarity: float
    weight: float
    score: float  # similarity * weight — what we rank and threshold on
    occurrences: int
    is_pattern: bool
    is_strong: bool


def _similarity(
    signature: IncidentSignature, query_vec: list[float] | None, pi: PastIncident
) -> float:
    if query_vec is not None and pi.embedding:
        return cosine(query_vec, pi.embedding)
    return lexical(signature.text, pi.signature_text)


async def recall(
    session: AsyncSession, signature: IncidentSignature, *, limit: int = 5
) -> list[Recollection]:
    settings = get_settings()
    repo = PastIncidentRepository(session)
    query_vec = embed_text(signature.text)

    # id -> (incident, best similarity seen)
    scored: dict[UUID, tuple[PastIncident, float]] = {}

    for pi in await repo.list_by_fingerprint(fingerprint(signature)):
        scored[pi.id] = (pi, _EXACT_FP_SIMILARITY)

    for pi in await repo.list_recent(limit=_CANDIDATE_POOL):
        sim = _similarity(signature, query_vec, pi)
        if pi.id in scored:
            existing, best = scored[pi.id]
            scored[pi.id] = (existing, max(best, sim))
        elif sim >= settings.memory_semantic_threshold:
            scored[pi.id] = (pi, sim)

    recollections: list[Recollection] = []
    for pi, sim in scored.values():
        score = round(sim * pi.weight, 4)
        recollections.append(
            Recollection(
                past_incident_id=pi.id,
                fingerprint=pi.fingerprint,
                service=pi.service,
                alert_type=pi.alert_type,
                root_cause=pi.root_cause,
                recommended_fix=pi.recommended_fix,
                similarity=round(sim, 4),
                weight=pi.weight,
                score=score,
                occurrences=pi.occurrences,
                is_pattern=pi.is_pattern,
                is_strong=score >= settings.memory_strong_match_threshold,
            )
        )

    # Best score first; prefer distilled patterns and higher occurrence counts on ties.
    recollections.sort(key=lambda r: (r.score, r.is_pattern, r.occurrences), reverse=True)
    return recollections[:limit]


async def recall_for_alert(alert: dict[str, object]) -> list[Recollection]:
    """Convenience for the investigator node: recall from a fresh read session.

    Best-effort — if memory is unavailable the investigation just proceeds cold.
    """
    try:
        async with session_factory() as session:
            return await recall(session, signature_from_alert(alert))
    except Exception as exc:  # noqa: BLE001 - memory optional
        log.warning("memory.recall_unavailable", error=str(exc))
        return []
