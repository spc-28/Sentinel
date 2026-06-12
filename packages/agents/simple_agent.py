"""A simple step-by-step investigating agent (LangChain + LiteLLM / Claude Sonnet).

It runs a bounded tool-calling loop: the model inspects logs/metrics/traces/deploys,
decides what to check next, and stops once it has a likely cause. A final structured
pass turns the free-text conclusion into ranked hypotheses.
"""

from __future__ import annotations

import json
import os
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_litellm import ChatLiteLLM
from pydantic import BaseModel, Field, ValidationError

from packages.agents.tools import ALL_TOOLS
from packages.core.config import get_settings

log = structlog.get_logger()

_SYSTEM_PROMPT = """You are a senior site-reliability engineer investigating a \
production incident. You have tools to inspect logs, metrics, traces and recent \
deploys for the affected service (and its dependencies).

Work step by step like a real engineer:
- Form a hypothesis, then use a tool to gather evidence for or against it.
- Follow the strongest signal (errors, latency spikes, anomalies, recent deploys).
- Be efficient: you have a limited number of tool calls, so don't repeat yourself.

When you are reasonably confident, STOP calling tools and reply with a short \
conclusion naming the most likely root cause(s) and the evidence behind them."""

_EXTRACT_PROMPT = """From the investigation conclusion and evidence below, produce \
up to 3 ranked root-cause hypotheses. Reply with ONLY a JSON object of the form:
{"hypotheses": [{"statement": "...", "description": "...", "confidence": 0.0-1.0, \
"rank": 1}]}
rank 1 = most likely. confidence is your 0-1 certainty. Return valid JSON only."""


class HypothesisDraft(BaseModel):
    statement: str
    description: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1, le=3)


class _Hypotheses(BaseModel):
    hypotheses: list[HypothesisDraft]


class InvestigationResult(BaseModel):
    summary: str
    hypotheses: list[HypothesisDraft]
    steps_used: int
    tools_used: list[str]
    transcript: list[str]


def _build_llm() -> ChatLiteLLM:
    settings = get_settings()
    if settings.anthropic_api_key:
        # LiteLLM reads the key from the environment; bridge it from Settings.
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    return ChatLiteLLM(model=settings.llm_model, temperature=0, max_tokens=2048)


def _text(content: Any) -> str:
    """Flatten a message's content (string or Anthropic content blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict)]
        return "\n".join(p for p in parts if p)
    return str(content)


def _alert_task(service: str, title: str, severity: str, payload: dict[str, Any]) -> str:
    return (
        f"Investigate this alert.\n"
        f"- service: {service}\n"
        f"- title: {title}\n"
        f"- severity: {severity}\n"
        f"- details: {json.dumps(payload, default=str)}\n\n"
        f"Find the most likely root cause."
    )


def _extract_hypotheses(
    llm: ChatLiteLLM, conclusion: str, transcript: list[str]
) -> list[HypothesisDraft]:
    evidence = "\n".join(transcript[-20:])
    response = llm.invoke(
        [
            SystemMessage(content=_EXTRACT_PROMPT),
            HumanMessage(content=f"CONCLUSION:\n{conclusion}\n\nEVIDENCE:\n{evidence}"),
        ]
    )
    raw = _text(response.content).strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    try:
        return _Hypotheses.model_validate_json(raw).hypotheses
    except (ValidationError, ValueError):
        log.warning("agent.extract_failed", raw=raw[:200])
        return [HypothesisDraft(statement=conclusion[:500] or "Unknown", confidence=0.3, rank=1)]


def run_investigation(
    service: str, title: str, severity: str, payload: dict[str, Any] | None = None
) -> InvestigationResult:
    """Run the bounded investigation loop and return ranked hypotheses (sync)."""
    settings = get_settings()
    max_steps = settings.agent_max_steps
    llm = _build_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    tool_map = {t.name: t for t in ALL_TOOLS}

    messages: list[Any] = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_alert_task(service, title, severity, payload or {})),
    ]
    transcript: list[str] = []
    tools_used: list[str] = []
    steps = 0
    final = ""

    while steps < max_steps:
        steps += 1
        ai: AIMessage = llm_with_tools.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            final = _text(ai.content)
            break
        for call in ai.tool_calls:
            name, args, call_id = call["name"], call["args"], call["id"]
            tools_used.append(name)
            try:
                observation = tool_map[name].invoke(args)
            except Exception as exc:  # noqa: BLE001 - report tool errors back to the model
                observation = f"ERROR: {exc}"
            transcript.append(f"{name}({json.dumps(args, default=str)}) -> {observation[:300]}")
            messages.append(ToolMessage(content=observation, tool_call_id=call_id))
    else:
        # Loop exhausted without a tool-free reply: ask for a final conclusion.
        messages.append(HumanMessage(content="Step budget reached. Give your best conclusion now."))
        final = _text(llm.invoke(messages).content)

    hypotheses = _extract_hypotheses(llm, final, transcript)
    log.info("agent.done", service=service, steps=steps, tools=len(tools_used))
    return InvestigationResult(
        summary=final,
        hypotheses=hypotheses,
        steps_used=steps,
        tools_used=tools_used,
        transcript=transcript,
    )
