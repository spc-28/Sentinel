"""Alert correlation: decide whether a new alert joins an existing incident group."""

from __future__ import annotations

from packages.core.enums import AlertSeverity

_SEVERITY_RANK: dict[AlertSeverity, int] = {
    AlertSeverity.info: 0,
    AlertSeverity.low: 1,
    AlertSeverity.medium: 2,
    AlertSeverity.high: 3,
    AlertSeverity.critical: 4,
}


def severity_rank(severity: AlertSeverity) -> int:
    return _SEVERITY_RANK.get(severity, 0)
