"""Model routing (Part 15 experiment): easy cases → local model, hard → Claude.

The chosen model for an investigation is stored in a context var that ``build_llm``
reads, so no node needs to change. Routing is off by default; enable it with
``MODEL_ROUTING_ENABLED=true`` once the local model is served.
"""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Iterator

from packages.core.config import get_settings

_model_override: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "sentinel_model_override", default=None
)

# Severities considered "routine" enough for the small local model.
_EASY_SEVERITIES = {"low", "info", "medium"}


def choose_model(*, severity: str, memory_hit: bool) -> str:
    """Pick the model for an investigation. Returns the Claude model unless routing is
    enabled and the case looks routine (a memory hit, or a lower-severity alert)."""
    settings = get_settings()
    if not settings.model_routing_enabled:
        return settings.llm_model
    routine = memory_hit or severity.lower() in _EASY_SEVERITIES
    return settings.local_llm_model if routine else settings.llm_model


def current_model_override() -> str | None:
    return _model_override.get()


@contextlib.contextmanager
def routed_model(model: str) -> Iterator[None]:
    token = _model_override.set(model)
    try:
        yield
    finally:
        _model_override.reset(token)
