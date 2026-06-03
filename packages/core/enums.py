"""Fixed choice sets for status/category columns (stored as native PG enums)."""

from __future__ import annotations

import enum


class AlertSeverity(enum.StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class AlertStatus(enum.StrEnum):
    received = "received"
    investigating = "investigating"
    resolved = "resolved"
    dismissed = "dismissed"


class IncidentStatus(enum.StrEnum):
    open = "open"
    mitigated = "mitigated"
    resolved = "resolved"
    closed = "closed"


class InvestigationStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class EvidenceSource(enum.StrEnum):
    logs = "logs"
    metrics = "metrics"
    traces = "traces"
    deploys = "deploys"
    vectors = "vectors"
    runbook = "runbook"
    other = "other"


class EvidenceStance(enum.StrEnum):
    """Whether a piece of evidence supports or argues against a hypothesis."""

    supporting = "supporting"
    refuting = "refuting"
    neutral = "neutral"
