"""Tiny eval harness: run each seed case through the graph and score the report.

From Part 5 on, this replaces eyeballing a single alert. Each case in
docs/eval/cases.jsonl has an input alert and a known root cause; we run the
five-agent graph and check whether the reported root cause matches (loose keyword
overlap). Prints a per-case result and an overall match rate.

Run: `make eval` (needs datastores up and ANTHROPIC_API_KEY set).
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Any

import structlog
from packages.agents.graph import run_graph
from packages.core.logging import configure_logging

log = structlog.get_logger()

CASES_PATH = Path(__file__).resolve().parent.parent / "docs" / "eval" / "cases.jsonl"
_MATCH_THRESHOLD = 0.5
_STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "and",
    "or",
    "is",
    "are",
    "was",
    "by",
    "for",
    "with",
    "due",
    "from",
    "at",
    "this",
    "that",
    "it",
    "caused",
    "causing",
    "increased",
    "too",
    "low",
}


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOPWORDS}


def matches(expected: str, reported: str) -> tuple[bool, float]:
    keys = _keywords(expected)
    if not keys:
        return False, 0.0
    overlap = len(keys & _keywords(reported)) / len(keys)
    return overlap >= _MATCH_THRESHOLD, round(overlap, 2)


def _load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASES_PATH.read_text().splitlines() if line.strip()]


async def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    alert = case["alert"]
    payload = {
        "service": case["service"],
        "title": alert["title"],
        "severity": alert["severity"],
        "details": alert.get("payload", {}),
    }
    thread_id = f"eval-{case['id']}-{uuid.uuid4().hex[:8]}"
    final = await run_graph(payload, thread_id)
    report = final.get("report")
    reported = report.root_cause if report is not None else ""
    ok, score = matches(case["expected_root_cause"], reported)
    return {"id": case["id"], "ok": ok, "score": score, "reported": reported}


async def main() -> None:
    configure_logging(level="WARNING")
    cases = _load_cases()
    results = [await _run_case(case) for case in cases]

    passed = sum(1 for r in results if r["ok"])
    print("\n=== Sentinel eval ===")
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"[{mark}] {r['id']:<24} overlap={r['score']:<4} -> {r['reported'][:80]}")
    print(f"\nroot-cause match rate: {passed}/{len(results)} = {passed / len(results):.0%}\n")


if __name__ == "__main__":
    asyncio.run(main())
