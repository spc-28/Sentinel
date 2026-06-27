"""Background job: merge similar past incidents into reusable patterns.

Recurring incidents are distilled into a single *pattern* row (``is_pattern=True``)
that records how often it happens, the representative cause/fix, and — when the
timing concentrates — a recurrence hint, e.g. "checkout slows every Monday 9am
because of the scheduled backup".

Two things become a pattern:

- several *distinct* memories that mean the same thing (clustered by embedding
  similarity, since exact duplicates are already collapsed by ``remember``), or
- a single memory that has *recurred* enough times (occurrence count).

Members are linked back to the pattern via ``pattern_id`` (re-runs reuse the
existing pattern), and recall prefers patterns because they aggregate several
confirmations into one trusted memory.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config import get_settings
from packages.core.db import session_factory
from packages.core.models import PastIncident
from packages.core.repositories import PastIncidentRepository
from packages.memory.similarity import cosine, lexical

log = structlog.get_logger()

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _member_similarity(a: PastIncident, b: PastIncident) -> float:
    if a.embedding and b.embedding:
        return cosine(a.embedding, b.embedding)
    return lexical(a.signature_text, b.signature_text)


def _cluster(incidents: Sequence[PastIncident], threshold: float) -> list[list[PastIncident]]:
    """Greedy single-pass clustering by meaning (each memory joins the first
    cluster whose representative it is similar enough to)."""
    clusters: list[list[PastIncident]] = []
    for incident in incidents:
        for cluster in clusters:
            if _member_similarity(incident, cluster[0]) >= threshold:
                cluster.append(incident)
                break
        else:
            clusters.append([incident])
    return clusters


def _recurrence_hint(members: Sequence[PastIncident]) -> str:
    """A "recurs ~<weekday> <hour>:00" note when member timings concentrate."""
    slots = Counter((m.last_seen_at.weekday(), m.last_seen_at.hour) for m in members)
    (weekday, hour), count = slots.most_common(1)[0]
    if count >= 2 and count >= len(members) / 2:
        return f" (recurs ~{_WEEKDAYS[weekday]} {hour:02d}:00)"
    return ""


def _label(representative: PastIncident, members: Sequence[PastIncident]) -> str:
    base = f"{representative.service}: {representative.alert_type} — {representative.root_cause}"
    return f"{base}{_recurrence_hint(members)}"


async def merge_patterns(session: AsyncSession | None = None) -> int:
    """Cluster similar memories into patterns. Returns the number of patterns."""
    if session is None:
        async with session_factory() as owned:
            merged = await _merge(owned)
            await owned.commit()
            return merged
    return await _merge(session)


async def _merge(session: AsyncSession) -> int:
    settings = get_settings()
    min_cluster = settings.memory_merge_min_cluster
    repo = PastIncidentRepository(session)

    incidents = await repo.list_incidents()
    patterns = 0
    for cluster in _cluster(incidents, settings.memory_merge_similarity):
        total_occurrences = sum(m.occurrences for m in cluster)
        # A pattern forms from several distinct memories or one that keeps recurring.
        if len(cluster) < min_cluster and total_occurrences < min_cluster:
            continue
        patterns += 1
        await _upsert_pattern(repo, cluster, total_occurrences)

    log.info("memory.merged", incidents=len(incidents), patterns=patterns)
    return patterns


async def _upsert_pattern(
    repo: PastIncidentRepository, cluster: Sequence[PastIncident], total_occurrences: int
) -> None:
    representative = max(cluster, key=lambda m: (m.weight, m.occurrences, m.last_seen_at))
    avg_weight = round(sum(m.weight for m in cluster) / len(cluster), 4)
    label = _label(representative, cluster)

    # Reuse a pattern any member already belongs to, so re-runs update in place.
    existing_id = next((m.pattern_id for m in cluster if m.pattern_id is not None), None)
    pattern = await repo.get(existing_id) if existing_id is not None else None

    if pattern is None:
        pattern = await repo.create(
            service=representative.service,
            alert_type=representative.alert_type,
            main_error=representative.main_error,
            fingerprint=representative.fingerprint,
            signature_text=representative.signature_text,
            title=representative.title,
            root_cause=representative.root_cause,
            recommended_fix=representative.recommended_fix,
            embedding=representative.embedding,
            weight=avg_weight,
            occurrences=total_occurrences,
            is_pattern=True,
            pattern_label=label,
            last_seen_at=representative.last_seen_at,
        )
    else:
        pattern.root_cause = representative.root_cause
        pattern.recommended_fix = representative.recommended_fix
        pattern.embedding = representative.embedding
        pattern.weight = avg_weight
        pattern.occurrences = total_occurrences
        pattern.pattern_label = label
        pattern.last_seen_at = representative.last_seen_at

    for member in cluster:
        member.pattern_id = pattern.id
    await repo.session.flush()
