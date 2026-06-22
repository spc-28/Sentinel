"""Combine the correlation strategies into a single group decision."""

from __future__ import annotations

import structlog

from packages.agents.correlation import by_dependency, by_meaning, by_time
from packages.agents.correlation.types import AlertView, GroupDecision, GroupView
from packages.core.config import Settings

log = structlog.get_logger()


def _score_group(
    alert: AlertView, group: GroupView, settings: Settings, connected_services: set[str]
) -> tuple[float, str | None]:
    """Best match score (and method) for the alert against one group."""
    window = settings.correlation_window_minutes
    if by_time.matches(alert, group, window):
        return 1.0, "time"
    if by_dependency.matches(alert, group, window, connected_services):
        return 0.7, "dependency"
    if settings.semantic_correlation_enabled:
        ok, sim = by_meaning.matches(alert, group, settings.semantic_similarity_threshold, window)
        if ok:
            return sim, "semantic"
    return 0.0, None


def correlate(
    alert: AlertView,
    groups: list[GroupView],
    settings: Settings,
    connected_services: set[str] | None = None,
) -> GroupDecision:
    """Return the best existing group for ``alert``, or a decision to start a new one."""
    connected = connected_services or set()
    best_id = None
    best_score = 0.0
    best_method: str | None = None
    for group in groups:
        score, method = _score_group(alert, group, settings, connected)
        if score > best_score:
            best_id, best_score, best_method = group.id, score, method

    if best_id is not None:
        log.info("correlation.matched", method=best_method, score=round(best_score, 3))
        return GroupDecision(best_id, is_new=False, method=best_method, score=round(best_score, 3))
    return GroupDecision(None, is_new=True, method=None, score=0.0)
