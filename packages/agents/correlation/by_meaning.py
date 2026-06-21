"""Semantic correlation (OPTIONAL): group alerts with similar text.

Off by default. Enable with ``SEMANTIC_CORRELATION_ENABLED=true`` and install the
extras: ``uv add sentence-transformers`` (pulls torch). Uses sentence-transformer
embeddings + cosine similarity for the streaming path; the batch equivalent would
cluster a set of titles with HDBSCAN. If the library isn't installed, this layer
quietly returns "no match".
"""

from __future__ import annotations

from typing import Any

import structlog

from packages.agents.correlation.by_time import within_window
from packages.agents.correlation.types import AlertView, GroupView

log = structlog.get_logger()

_model: Any = None


def _get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # lazy: heavy import

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def similarity(text_a: str, text_b: str) -> float:
    try:
        model = _get_model()
    except Exception as exc:  # noqa: BLE001 - missing extra → disable gracefully
        log.warning("correlation.semantic_unavailable", error=str(exc))
        return 0.0
    import numpy as np

    a, b = model.encode([text_a, text_b])
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def matches(
    alert: AlertView, group: GroupView, threshold: float, window_minutes: int
) -> tuple[bool, float]:
    if not within_window(alert, group, window_minutes):
        return False, 0.0
    score = similarity(alert.title, group.title)
    return score >= threshold, score
