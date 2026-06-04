"""Pydantic schemas for transferring domain data over the API.

For each model: a *Create* (input), an *Update* (all-optional input) and a
*Read* (output, populated from ORM objects) schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.core.enums import (
    AlertSeverity,
    AlertStatus,
    EvidenceSource,
    EvidenceStance,
    IncidentStatus,
    InvestigationStatus,
)


class _Read(BaseModel):
    """Base for output schemas: read from ORM attributes, carries id + timestamps."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# --- Service -------------------------------------------------------------
class ServiceBase(BaseModel):
    name: str
    team: str | None = None
    repo_url: str | None = None
    description: str | None = None


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = None
    team: str | None = None
    repo_url: str | None = None
    description: str | None = None


class ServiceRead(ServiceBase, _Read):
    pass


# --- Alert ---------------------------------------------------------------
class AlertBase(BaseModel):
    service_id: UUID | None = None
    title: str
    severity: AlertSeverity
    source: str | None = None
    fingerprint: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    triggered_at: datetime | None = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: AlertStatus | None = None
    severity: AlertSeverity | None = None


class AlertRead(AlertBase, _Read):
    status: AlertStatus


class AlertWebhook(BaseModel):
    """Incoming alert payload (a common webhook shape)."""

    service: str | None = None  # service name; resolved to service_id if known
    title: str
    severity: AlertSeverity = AlertSeverity.medium
    source: str | None = None
    fingerprint: str | None = None
    triggered_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


# --- Incident ------------------------------------------------------------
class IncidentBase(BaseModel):
    alert_id: UUID
    service_id: UUID | None = None
    title: str
    started_at: datetime | None = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    title: str | None = None
    status: IncidentStatus | None = None
    resolved_at: datetime | None = None


class IncidentRead(IncidentBase, _Read):
    status: IncidentStatus
    resolved_at: datetime | None = None


# --- Investigation -------------------------------------------------------
class InvestigationBase(BaseModel):
    incident_id: UUID


class InvestigationCreate(InvestigationBase):
    pass


class InvestigationUpdate(BaseModel):
    status: InvestigationStatus | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class InvestigationRead(InvestigationBase, _Read):
    status: InvestigationStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


# --- Hypothesis ----------------------------------------------------------
class HypothesisBase(BaseModel):
    investigation_id: UUID
    statement: str
    description: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1, le=3)


class HypothesisCreate(HypothesisBase):
    pass


class HypothesisUpdate(BaseModel):
    statement: str | None = None
    description: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    rank: int | None = Field(default=None, ge=1, le=3)


class HypothesisRead(HypothesisBase, _Read):
    pass


# --- Evidence ------------------------------------------------------------
class EvidenceBase(BaseModel):
    hypothesis_id: UUID
    source: EvidenceSource
    stance: EvidenceStance = EvidenceStance.neutral
    content: str
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    reference: str | None = None


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceUpdate(BaseModel):
    stance: EvidenceStance | None = None
    content: str | None = None
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class EvidenceRead(EvidenceBase, _Read):
    pass


# --- RCAReport -----------------------------------------------------------
class RCAReportBase(BaseModel):
    investigation_id: UUID
    summary: str | None = None
    root_cause: str
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    recommended_fix: str | None = None


class RCAReportCreate(RCAReportBase):
    pass


class RCAReportUpdate(BaseModel):
    summary: str | None = None
    root_cause: str | None = None
    timeline: list[dict[str, Any]] | None = None
    recommended_fix: str | None = None


class RCAReportRead(RCAReportBase, _Read):
    pass


# --- Runbook -------------------------------------------------------------
class RunbookBase(BaseModel):
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)


class RunbookCreate(RunbookBase):
    pass


class RunbookUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class RunbookRead(RunbookBase, _Read):
    pass
