"""Thin data-access layer: one repository per model, plus a generic CRUD base."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import GroupStatus, InvestigationStatus
from packages.core.models import (
    Alert,
    Base,
    Evidence,
    Hypothesis,
    Incident,
    IncidentGroup,
    Investigation,
    PastIncident,
    RCAReport,
    Runbook,
    Service,
)


class BaseRepository[ModelT: Base]:
    """Generic create/read/update/delete for a single model.

    Methods flush (so generated ids are available) but do not commit; the caller
    owns the transaction.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **values: Any) -> ModelT:
        obj = self.model(**values)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get(self, id_: UUID) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        result = await self.session.execute(select(self.model).limit(limit).offset(offset))
        return result.scalars().all()

    async def update(self, id_: UUID, **values: Any) -> ModelT | None:
        obj = await self.get(id_)
        if obj is None:
            return None
        for key, value in values.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id_: UUID) -> bool:
        obj = await self.get(id_)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True


class ServiceRepository(BaseRepository[Service]):
    model = Service

    async def get_by_name(self, name: str) -> Service | None:
        result = await self.session.execute(select(Service).where(Service.name == name))
        return result.scalar_one_or_none()


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    async def list_for_group(self, group_id: UUID) -> Sequence[Alert]:
        result = await self.session.execute(
            select(Alert).where(Alert.group_id == group_id).order_by(Alert.created_at)
        )
        return result.scalars().all()


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    async def get_by_alert(self, alert_id: UUID) -> Incident | None:
        result = await self.session.execute(
            select(Incident)
            .where(Incident.alert_id == alert_id)
            .order_by(Incident.created_at.desc())
        )
        return result.scalars().first()

    async def list_recent(
        self, since: datetime, *, service_id: UUID | None = None, limit: int = 50
    ) -> Sequence[Incident]:
        stmt = select(Incident).where(Incident.started_at >= since)
        if service_id is not None:
            stmt = stmt.where(Incident.service_id == service_id)
        stmt = stmt.order_by(Incident.started_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class IncidentGroupRepository(BaseRepository[IncidentGroup]):
    model = IncidentGroup

    async def list_open_since(self, since: datetime) -> Sequence[IncidentGroup]:
        result = await self.session.execute(
            select(IncidentGroup)
            .where(IncidentGroup.status == GroupStatus.open)
            .where(IncidentGroup.last_activity_at >= since)
            .order_by(IncidentGroup.last_activity_at.desc())
        )
        return result.scalars().all()


class InvestigationRepository(BaseRepository[Investigation]):
    model = Investigation

    async def list_running(self) -> Sequence[Investigation]:
        result = await self.session.execute(
            select(Investigation).where(Investigation.status == InvestigationStatus.running)
        )
        return result.scalars().all()

    async def get_by_incident(self, incident_id: UUID) -> Investigation | None:
        result = await self.session.execute(
            select(Investigation)
            .where(Investigation.incident_id == incident_id)
            .order_by(Investigation.created_at.desc())
        )
        return result.scalars().first()

    async def cost_stats(self) -> tuple[int, float, float, int]:
        """(count, avg cost, total cost, total tokens) over investigations with a cost."""
        result = await self.session.execute(
            select(
                func.count(Investigation.id),
                func.coalesce(func.avg(Investigation.cost_usd), 0.0),
                func.coalesce(func.sum(Investigation.cost_usd), 0.0),
                func.coalesce(
                    func.sum(
                        func.coalesce(Investigation.input_tokens, 0)
                        + func.coalesce(Investigation.output_tokens, 0)
                    ),
                    0,
                ),
            ).where(Investigation.cost_usd.is_not(None))
        )
        count, avg, total, tokens = result.one()
        return int(count), float(avg), float(total), int(tokens)


class HypothesisRepository(BaseRepository[Hypothesis]):
    model = Hypothesis

    async def list_for_investigation(self, investigation_id: UUID) -> Sequence[Hypothesis]:
        result = await self.session.execute(
            select(Hypothesis)
            .where(Hypothesis.investigation_id == investigation_id)
            .order_by(Hypothesis.rank)
        )
        return result.scalars().all()


class EvidenceRepository(BaseRepository[Evidence]):
    model = Evidence


class RCAReportRepository(BaseRepository[RCAReport]):
    model = RCAReport

    async def get_for_investigation(self, investigation_id: UUID) -> RCAReport | None:
        result = await self.session.execute(
            select(RCAReport).where(RCAReport.investigation_id == investigation_id)
        )
        return result.scalar_one_or_none()

    async def search(self, query: str, *, limit: int = 10) -> Sequence[RCAReport]:
        like = f"%{query}%"
        result = await self.session.execute(
            select(RCAReport)
            .where(
                or_(
                    RCAReport.root_cause.ilike(like),
                    RCAReport.summary.ilike(like),
                    RCAReport.recommended_fix.ilike(like),
                )
            )
            .order_by(RCAReport.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


class RunbookRepository(BaseRepository[Runbook]):
    model = Runbook

    async def get_by_title(self, title: str) -> Runbook | None:
        result = await self.session.execute(select(Runbook).where(Runbook.title == title))
        return result.scalar_one_or_none()


class PastIncidentRepository(BaseRepository[PastIncident]):
    model = PastIncident

    async def get_by_fingerprint(self, fingerprint: str) -> PastIncident | None:
        """The single remembered incident for this fingerprint (not a merged pattern)."""
        result = await self.session.execute(
            select(PastIncident)
            .where(PastIncident.fingerprint == fingerprint)
            .where(PastIncident.is_pattern.is_(False))
        )
        return result.scalars().first()

    async def list_by_fingerprint(self, fingerprint: str) -> Sequence[PastIncident]:
        """Everything (incidents + pattern) sharing a fingerprint — for exact recall."""
        result = await self.session.execute(
            select(PastIncident).where(PastIncident.fingerprint == fingerprint)
        )
        return result.scalars().all()

    async def get_pattern_by_fingerprint(self, fingerprint: str) -> PastIncident | None:
        result = await self.session.execute(
            select(PastIncident)
            .where(PastIncident.fingerprint == fingerprint)
            .where(PastIncident.is_pattern.is_(True))
        )
        return result.scalars().first()

    async def get_by_investigation(self, investigation_id: UUID) -> PastIncident | None:
        result = await self.session.execute(
            select(PastIncident)
            .where(PastIncident.investigation_id == investigation_id)
            .where(PastIncident.is_pattern.is_(False))
            .order_by(PastIncident.created_at.desc())
        )
        return result.scalars().first()

    async def list_recent(self, *, limit: int = 200) -> Sequence[PastIncident]:
        """Recent memories and patterns, newest first — the recall candidate pool."""
        result = await self.session.execute(
            select(PastIncident).order_by(PastIncident.last_seen_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def list_incidents(self, *, limit: int = 1000) -> Sequence[PastIncident]:
        """Raw memories only (excludes merged patterns) — input to the merge job."""
        result = await self.session.execute(
            select(PastIncident)
            .where(PastIncident.is_pattern.is_(False))
            .order_by(PastIncident.last_seen_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
