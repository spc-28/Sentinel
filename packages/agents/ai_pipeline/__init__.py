"""AI-system failure detection — Sentinel's differentiating capability."""

from __future__ import annotations

from typing import Any

_AI_KEYWORDS = (
    "embedding",
    "drift",
    "rag",
    "prompt",
    "vector",
    "index",
    "ai cost",
    "model version",
)


def is_ai_alert(alert: dict[str, Any]) -> bool:
    """Whether an alert is about the AI pipeline (routes to the AI investigator branch)."""
    details = alert.get("details", {})
    if isinstance(details, dict) and details.get("category") == "ai_pipeline":
        return True
    title = str(alert.get("title", "")).lower()
    return any(keyword in title for keyword in _AI_KEYWORDS)
