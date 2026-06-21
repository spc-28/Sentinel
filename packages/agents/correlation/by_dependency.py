"""Dependency-based correlation: alerts on connected services within the window.

PLACEHOLDER service graph until Part 7 builds the real dependency map. Edges are
treated as bidirectional.
"""

from __future__ import annotations

from packages.agents.correlation.by_time import within_window
from packages.agents.correlation.types import AlertView, GroupView

_DEPENDENCIES: dict[str, set[str]] = {
    "checkout-api": {"auth-service", "inventory-service"},
    "search-api": {"inventory-service"},
    "notifications-worker": {"auth-service"},
}


def connected(a: str, b: str) -> bool:
    if a == b:
        return False
    return b in _DEPENDENCIES.get(a, set()) or a in _DEPENDENCIES.get(b, set())


def matches(alert: AlertView, group: GroupView, window_minutes: int) -> bool:
    if group.service is None:
        return False
    return connected(alert.service, group.service) and within_window(alert, group, window_minutes)
