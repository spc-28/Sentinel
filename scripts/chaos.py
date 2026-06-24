"""Inject an AI-pipeline fault and post a matching alert so Sentinel investigates.

    python -m scripts.chaos embedding_drift     # drift on the runbooks index
    python -m scripts.chaos search_quality      # RAG answer quality drop
    python -m scripts.chaos prompt_regression   # bad prompt shipped
    python -m scripts.chaos cost_spike          # AI spend spike
    python -m scripts.chaos clear               # clear all injected faults

Each fault is a free eval case: the true cause is known at injection time.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import httpx
import structlog
from packages.agents.ai_pipeline import chaos
from packages.core.logging import configure_logging

log = structlog.get_logger()

_SCENARIOS: dict[str, dict[str, str]] = {
    "embedding_drift": {
        "target": "runbooks",
        "service": "search-api",
        "index": "runbooks",
        "title": "Embedding drift suspected on runbooks index",
    },
    "search_quality": {
        "target": "runbooks",
        "service": "search-api",
        "index": "runbooks",
        "title": "RAG answer quality dropped",
    },
    "prompt_regression": {
        "target": "checkout-api",
        "service": "checkout-api",
        "index": "runbooks",
        "title": "Prompt regression after deploy",
    },
    "cost_spike": {
        "target": "checkout-api",
        "service": "checkout-api",
        "index": "runbooks",
        "title": "AI cost spike detected",
    },
}


async def main() -> None:
    configure_logging()
    command = sys.argv[1] if len(sys.argv) > 1 else ""

    if command == "clear":
        cleared = await chaos.clear_all()
        print(f"cleared {cleared} injected fault(s)")
        return

    scenario = _SCENARIOS.get(command)
    if scenario is None:
        print(f"usage: python -m scripts.chaos [{'|'.join(_SCENARIOS)}|clear]")
        raise SystemExit(2)

    await chaos.inject(command, scenario["target"])
    print(f"injected '{command}' on '{scenario['target']}'")

    alert: dict[str, Any] = {
        "service": scenario["service"],
        "title": scenario["title"],
        "severity": "high",
        "payload": {"category": "ai_pipeline", "fault": command, "index": scenario["index"]},
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/webhooks/alert", json=alert, timeout=10
            )
        print(f"alert posted: {response.status_code} {response.json()}")
    except Exception as exc:  # noqa: BLE001 - API may not be running
        print(f"could not post alert (is the API up?): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
