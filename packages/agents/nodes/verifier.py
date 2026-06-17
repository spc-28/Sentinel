"""Verifier — scores each hypothesis against the gathered evidence.

Placeholder scoring (keyword overlap between the hypothesis and the evidence text)
to be replaced by RAG / an LLM judge in a later part. A hypothesis is "supported"
when its overlap score clears the threshold.
"""

from __future__ import annotations

import re

import structlog

from packages.agents.state import GraphState, VerifiedHypothesis

log = structlog.get_logger()

_SUPPORT_THRESHOLD = 0.34
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
    "were",
    "by",
    "for",
    "with",
    "due",
    "from",
    "at",
    "this",
    "that",
    "it",
}


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _score(statement: str, evidence_words: set[str]) -> float:
    keys = _keywords(statement)
    if not keys:
        return 0.0
    return len(keys & evidence_words) / len(keys)


def verify(state: GraphState) -> dict[str, object]:
    evidence = state.get("evidence", [])
    evidence_words = _keywords(" ".join(f"{e.summary} {e.detail or ''}" for e in evidence))

    verified: list[VerifiedHypothesis] = []
    for hyp in state.get("hypotheses", []):
        score = round(_score(f"{hyp.statement} {hyp.description or ''}", evidence_words), 3)
        verdict = (
            "supported"
            if score >= _SUPPORT_THRESHOLD
            else "inconclusive"
            if score > 0
            else "unsupported"
        )
        verified.append(
            VerifiedHypothesis(
                statement=hyp.statement,
                description=hyp.description,
                confidence=hyp.confidence,
                rank=hyp.rank,
                support_score=score,
                verdict=verdict,
            )
        )

    verified.sort(key=lambda v: (v.support_score, v.confidence), reverse=True)
    for rank, vh in enumerate(verified[:5], start=1):
        vh.rank = rank

    attempts = state.get("verify_attempts", 0) + 1
    supported = sum(1 for v in verified if v.verdict == "supported")
    log.info("node.verifier", attempt=attempts, supported=supported, total=len(verified))
    return {"verified": verified, "verify_attempts": attempts}
