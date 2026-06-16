"""Shared LLM access for the agent nodes (Claude Sonnet via LiteLLM)."""

from __future__ import annotations

import os
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLM
from pydantic import BaseModel, ValidationError

from packages.core.config import get_settings

log = structlog.get_logger()


def build_llm(*, max_tokens: int = 2048) -> ChatLiteLLM:
    settings = get_settings()
    if settings.anthropic_api_key:
        # LiteLLM reads the key from the environment; bridge it from Settings.
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    return ChatLiteLLM(model=settings.llm_model, temperature=0, max_tokens=max_tokens)


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
    raw = _strip_fences(text_of((await llm.ainvoke(messages)).content))
    try:
        return schema.model_validate_json(raw)
    except (ValidationError, ValueError):
        messages.append(
            HumanMessage(content="That was not valid JSON. Reply with valid JSON only.")
        )
        raw = _strip_fences(text_of((await llm.ainvoke(messages)).content))
        return schema.model_validate_json(raw)
