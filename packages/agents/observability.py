"""Observability: Langfuse tracing + LiteLLM token/cost tracking (Part 12).

Two independent concerns:
- **Cost/tokens** — a LiteLLM callback accumulates ``response_cost`` and token usage
  into a context-local ``Usage`` for the current investigation. Always on; used to
  fill ``Investigation.cost_usd``.
- **Tracing** — when Langfuse keys are set, each investigation becomes one trace:
  the graph run nests under it (nodes + LLM generations via the LangChain handler),
  and each tool call is added as a span. All gated so it's a no-op without keys.
"""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import litellm
import structlog
from litellm.integrations.custom_logger import CustomLogger

from packages.core.config import get_settings

log = structlog.get_logger()


@dataclass
class Usage:
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


_usage: contextvars.ContextVar[Usage | None] = contextvars.ContextVar(
    "sentinel_usage", default=None
)
_trace: contextvars.ContextVar[Any | None] = contextvars.ContextVar("sentinel_trace", default=None)

_client: Any = None
_configured = False


class _CostCallback(CustomLogger):
    """Accumulate LiteLLM cost + tokens into the current investigation's Usage."""

    def _record(self, kwargs: dict[str, Any], response_obj: Any) -> None:
        usage = _usage.get()
        if usage is None:
            return
        usage.cost_usd += float(kwargs.get("response_cost") or 0.0)
        token_usage = getattr(response_obj, "usage", None)
        if token_usage is not None:
            usage.input_tokens += int(getattr(token_usage, "prompt_tokens", 0) or 0)
            usage.output_tokens += int(getattr(token_usage, "completion_tokens", 0) or 0)

    def log_success_event(
        self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any
    ) -> None:
        self._record(kwargs, response_obj)

    async def async_log_success_event(
        self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any
    ) -> None:
        self._record(kwargs, response_obj)


def configure_observability() -> None:
    """Register the cost callback and (if keys are set) the Langfuse client. Call once."""
    global _client, _configured
    if _configured:
        return
    litellm.callbacks = [_CostCallback()]

    settings = get_settings()
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        log.info("observability.langfuse_enabled", host=settings.langfuse_host)
    _configured = True


@contextlib.contextmanager
def track_usage() -> Iterator[Usage]:
    """Accumulate LLM cost/tokens for everything run inside the block."""
    usage = Usage()
    token = _usage.set(usage)
    try:
        yield usage
    finally:
        _usage.reset(token)


@contextlib.contextmanager
def investigation_trace(name: str, **metadata: Any) -> Iterator[None]:
    """Open one Langfuse trace for an investigation (no-op if Langfuse is off)."""
    if _client is None:
        yield
        return
    trace = _client.trace(name=name, tags=["investigation"], metadata=metadata)
    token = _trace.set(trace)
    try:
        yield
    finally:
        _trace.reset(token)
        with contextlib.suppress(Exception):
            _client.flush()


def current_langchain_handler() -> Any | None:
    """A LangChain callback handler bound to the current investigation trace, if any."""
    trace = _trace.get()
    return trace.get_langchain_handler() if trace is not None else None


@contextlib.contextmanager
def tool_span(name: str) -> Iterator[None]:
    """Record one tool call as a span under the current trace (no-op if Langfuse is off)."""
    trace = _trace.get()
    if trace is None:
        yield
        return
    span = trace.span(name=name)
    try:
        yield
    finally:
        with contextlib.suppress(Exception):
            span.end()
