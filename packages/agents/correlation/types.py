"""Lightweight views passed to the correlation strategies (ORM-free)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from packages.core.enums import AlertSeverity


@dataclass(frozen=True)
class AlertView:
    id: UUID
    service: str
    title: str
    severity: AlertSeverity
    triggered_at: datetime


@dataclass(frozen=True)
class GroupView:
    id: UUID
    service: str | None
    title: str  # the group's leading/representative title
    leader_severity: AlertSeverity
    last_activity: datetime


@dataclass(frozen=True)
class GroupDecision:
    matched_group_id: UUID | None
    is_new: bool
    method: str | None  # time | dependency | semantic
    score: float
