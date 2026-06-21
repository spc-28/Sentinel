"""Time-based correlation: same service, alerts firing within a few minutes."""

from __future__ import annotations

from packages.agents.correlation.types import AlertView, GroupView


def within_window(alert: AlertView, group: GroupView, window_minutes: int) -> bool:
    delta = abs((alert.triggered_at - group.last_activity).total_seconds())
    return delta <= window_minutes * 60


def matches(alert: AlertView, group: GroupView, window_minutes: int) -> bool:
    return alert.service == group.service and within_window(alert, group, window_minutes)
