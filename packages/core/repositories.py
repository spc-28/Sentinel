"""Thin data-access layer: one repository per model, plus a generic CRUD base."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import (
    Alert,
    Base,
    Evidence,
    Hypothesis,
    Incident,
    Investigation,
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


class IncidentRepository(BaseRepository[Incident]):
    model = Incident


class InvestigationRepository(BaseRepository[Investigation]):
    model = Investigation


class HypothesisRepository(BaseRepository[Hypothesis]):
    model = Hypothesis


class EvidenceRepository(BaseRepository[Evidence]):
    model = Evidence


class RCAReportRepository(BaseRepository[RCAReport]):
    model = RCAReport


class RunbookRepository(BaseRepository[Runbook]):
    model = Runbook

    async def get_by_title(self, title: str) -> Runbook | None:
        result = await self.session.execute(select(Runbook).where(Runbook.title == title))
        return result.scalar_one_or_none()
