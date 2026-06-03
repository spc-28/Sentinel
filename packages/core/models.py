"""SQLAlchemy ORM models for the Sentinel domain.

Every table uses a UUID primary key and carries created_at/updated_at timestamps
(via the shared mixins). Status-like columns use native PG enums.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from packages.core.enums import (
    AlertSeverity,
    AlertStatus,
    EvidenceSource,
    EvidenceStance,
    IncidentStatus,
    InvestigationStatus,
)


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Service(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "services"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    team: Mapped[str | None] = mapped_column(String(255))
    repo_url: Mapped[str | None] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text)


class Alert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity, name="alert_severity"))
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"), default=AlertStatus.received
    )
    source: Mapped[str | None] = mapped_column(String(255))
    fingerprint: Mapped[str | None] = mapped_column(String(512), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Incident(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "incidents"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"), default=IncidentStatus.open
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Investigation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investigations"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, name="investigation_status"),
        default=InvestigationStatus.pending,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class Hypothesis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "hypotheses"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_hypothesis_confidence_range"
        ),
        CheckConstraint("rank IN (1, 2, 3)", name="ck_hypothesis_rank_values"),
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    statement: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)  # 0..1
    rank: Mapped[int] = mapped_column(Integer)  # 1, 2 or 3


class Evidence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evidence"

    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hypotheses.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[EvidenceSource] = mapped_column(Enum(EvidenceSource, name="evidence_source"))
    stance: Mapped[EvidenceStance] = mapped_column(
        Enum(EvidenceStance, name="evidence_stance"), default=EvidenceStance.neutral
    )
    content: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)  # relevance/match score, 0..1
    reference: Mapped[str | None] = mapped_column(String(1024))


class RCAReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "rca_reports"

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), unique=True, index=True
    )
    summary: Mapped[str | None] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    recommended_fix: Mapped[str | None] = mapped_column(Text)


class Runbook(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "runbooks"

    title: Mapped[str] = mapped_column(String(512), index=True)
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
