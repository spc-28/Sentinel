"""Eval harness with sub-commands. From Part 5 on, this replaces eyeballing.

    python -m scripts.eval graph       # root-cause match rate over cases.jsonl (needs LLM)
    python -m scripts.eval retrieval   # recall@3 over retrieval.jsonl
    python -m scripts.eval verifier    # NLI accuracy over verifier.jsonl

Default (no arg) runs the graph eval.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

import structlog
from packages.core.config import get_settings
from packages.core.logging import configure_logging

log = structlog.get_logger()

_EVAL_DIR = Path(__file__).resolve().parent.parent / "docs" / "eval"
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "and", "or", "is", "are", "was", "by",
    "for", "with", "due", "from", "at", "this", "that", "it", "caused", "causing",
    "increased", "too", "low",
}  # fmt: skip


def _load(name: str) -> list[dict[str, Any]]:
    path = _EVAL_DIR / name
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOPWORDS}


# --- graph: root-cause match rate ----------------------------------------
async def eval_graph() -> None:
    from packages.agents.graph import run_graph

    cases = _load("cases.jsonl")
    passed = 0
    print("\n=== graph: root-cause match ===")
    for case in cases:
        alert = case["alert"]
        payload = {
            "service": case["service"],
            "title": alert["title"],
            "severity": alert["severity"],
            "details": alert.get("payload", {}),
        }
        final = await run_graph(payload, f"eval-{case['id']}-{uuid.uuid4().hex[:8]}")
        report = final.get("report")
        reported = report.root_cause if report is not None else ""
        keys = _keywords(case["expected_root_cause"])
        overlap = len(keys & _keywords(reported)) / len(keys) if keys else 0.0
        ok = overlap >= 0.5
        passed += ok
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {case['id']:<22} overlap={overlap:.2f} -> {reported[:55]}")
    print(f"\nroot-cause match rate: {passed}/{len(cases)} = {passed / len(cases):.0%}\n")


# --- retrieval: recall@3 -------------------------------------------------
async def eval_retrieval() -> None:
    from packages.rag import store
    from packages.rag.retriever import search_runbooks

    from scripts.ingest_runbooks import ingest

    await ingest()  # ensure runbooks are embedded (idempotent)

    pairs = _load("retrieval.jsonl")
    hits = 0
    print("\n=== retrieval: recall@3 ===")
    for pair in pairs:
        expected = (
            {pair["expected"]} if isinstance(pair["expected"], str) else set(pair["expected"])
        )
        top3 = [h.title for h in await search_runbooks(pair["query"], top_k=3)]
        found = bool(expected & set(top3))
        hits += found
        print(f"[{'HIT ' if found else 'MISS'}] {pair['query']:<32} -> {top3}")
    await store.close()
    print(f"\nrecall@3: {hits}/{len(pairs)} = {hits / len(pairs):.0%}\n")


# --- verifier: NLI accuracy ----------------------------------------------
async def eval_verifier() -> None:
    from packages.rag.nli import support_score

    threshold = get_settings().nli_support_threshold
    pairs = _load("verifier.jsonl")
    correct = 0
    print(f"\n=== verifier: NLI accuracy (threshold {threshold}) ===")
    for pair in pairs:
        score = support_score(pair["evidence"], pair["hypothesis"])
        predicted = score >= threshold
        ok = predicted == pair["should_support"]
        correct += ok
        mark = "OK  " if ok else "WRONG"
        expect = str(pair["should_support"])
        print(f"[{mark}] support={score:.2f} expect={expect:<5} {pair['hypothesis'][:34]}")
    print(f"\nverifier accuracy: {correct}/{len(pairs)} = {correct / len(pairs):.0%}\n")


_COMMANDS = {"graph": eval_graph, "retrieval": eval_retrieval, "verifier": eval_verifier}


async def main() -> None:
    configure_logging(level="WARNING")
    command = sys.argv[1] if len(sys.argv) > 1 else "graph"
    runner = _COMMANDS.get(command)
    if runner is None:
        print(f"unknown command '{command}'. choices: {', '.join(_COMMANDS)}")
        raise SystemExit(2)
    await runner()


if __name__ == "__main__":
    asyncio.run(main())
