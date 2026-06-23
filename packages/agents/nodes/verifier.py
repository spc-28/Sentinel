"""Verifier — scores each hypothesis against the evidence with an NLI model.

Each hypothesis is split into small claims; each claim is checked for entailment
against the concatenated evidence with DeBERTa-MNLI; the claim scores are averaged.
No LLM call per hypothesis — cheap and deterministic at scale.
"""

from __future__ import annotations

import re

import structlog

from packages.agents.state import GraphState, VerifiedHypothesis
from packages.core.config import get_settings
from packages.rag.nli import support_score

log = structlog.get_logger()


def _claims(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|[;\n]", text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


def _evidence_text(state: GraphState) -> str:
    return "\n".join(
        f"{e.source}: {e.summary} {e.detail or ''}".strip() for e in state.get("evidence", [])
    )


def verify(state: GraphState) -> dict[str, object]:
    threshold = get_settings().nli_support_threshold
    evidence = _evidence_text(state)

    verified: list[VerifiedHypothesis] = []
    for hyp in state.get("hypotheses", []):
        claims = _claims(f"{hyp.statement}. {hyp.description or ''}")
        scores = [support_score(evidence, claim) for claim in claims] if evidence else []
        score = round(sum(scores) / len(scores), 3) if scores else 0.0
        verdict = (
            "supported" if score >= threshold else "inconclusive" if score > 0.15 else "unsupported"
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
