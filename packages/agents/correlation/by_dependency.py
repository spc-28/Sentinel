"""Dependency-based correlation: alerts on connected services within the window.

Connectivity comes from the Neo4j service map (Part 7), passed in as a resolved
set of neighbour service names so this stays synchronous and side-effect free.
"""

from __future__ import annotations

from packages.agents.correlation.by_time import within_window
from packages.agents.correlation.types import AlertView, GroupView


def matches(
    alert: AlertView, group: GroupView, window_minutes: int, connected_services: set[str]
) -> bool:
    if group.service is None:
        return False
    return group.service in connected_services and within_window(alert, group, window_minutes)
