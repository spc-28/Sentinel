"""Shared LLM access for the agent nodes (Claude Sonnet via LiteLLM)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLM
from litellm.exceptions import (
    APIConnectionError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from pydantic import BaseModel, ValidationError

from packages.core.config import get_settings

log = structlog.get_logger()

# Transient provider errors worth retrying — notably Anthropic's "overloaded_error",
# which LiteLLM surfaces as InternalServerError.
_RETRYABLE_ERRORS = (
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    APIConnectionError,
    Timeout,
)
_MAX_ATTEMPTS = 4


async def _ainvoke(llm: ChatLiteLLM, messages: list[Any]) -> Any:
    """Invoke the model, retrying transient upstream errors (overloaded, rate limit,
    timeout) with exponential backoff so a brief provider blip doesn't fail a run."""
    delay = 1.0
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return await llm.ainvoke(messages)
        except _RETRYABLE_ERRORS as exc:
            if attempt == _MAX_ATTEMPTS:
                raise
            log.warning("llm.transient_retry", attempt=attempt, delay=delay, error=str(exc))
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")  # loop always returns or raises


def build_llm(*, max_tokens: int = 2048) -> ChatLiteLLM:
    from packages.agents.routing import current_model_override

    settings = get_settings()
    model = current_model_override() or settings.llm_model
    kwargs: dict[str, Any] = {"model": model, "temperature": 0, "max_tokens": max_tokens}
    if model == settings.local_llm_model:
        # Local OpenAI-compatible server (the fine-tuned Qwen).
        kwargs["api_base"] = settings.local_llm_base_url
        kwargs["api_key"] = settings.local_llm_api_key
    elif settings.anthropic_api_key:
        # LiteLLM reads the key from the environment; bridge it from Settings.
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    return ChatLiteLLM(**kwargs)


def text_of(content: Any) -> str:
    """Flatten a message's content (string or Anthropic content blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict)]
        return "\n".join(p for p in parts if p)
    return str(content)


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    return raw


async def structured[M: BaseModel](system: str, human: str, schema: type[M]) -> M:
    """Ask the model for JSON and parse it into ``schema`` (one retry on failure)."""
    llm = build_llm()
    messages = [SystemMessage(content=system), HumanMessage(content=human)]
    raw = _strip_fences(text_of((await _ainvoke(llm, messages)).content))
    try:
        return schema.model_validate_json(raw)
    except (ValidationError, ValueError):
        messages.append(
            HumanMessage(content="That was not valid JSON. Reply with valid JSON only.")
        )
        raw = _strip_fences(text_of((await _ainvoke(llm, messages)).content))
        return schema.model_validate_json(raw)
