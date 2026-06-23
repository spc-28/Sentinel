"""Entailment scoring with a small NLI model (DeBERTa-MNLI cross-encoder).

Checking whether evidence supports a claim is a natural-language-inference task: a
small NLI model does it deterministically and cheaply — no LLM call per hypothesis.
Model loads lazily; scores are cached by (premise, claim).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

MODEL_NAME = "cross-encoder/nli-deberta-v3-base"
# Label order emitted by nli-deberta-v3-base logits.
_ENTAILMENT_INDEX = 1  # (contradiction, entailment, neutral)

_model: Any = None


def _get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder  # heavy: torch

        _model = CrossEncoder(MODEL_NAME)
    return _model


@lru_cache(maxsize=4096)
def entailment(premise: str, claim: str) -> float:
    """Probability that ``premise`` entails ``claim`` (0..1)."""
    import numpy as np

    logits = np.asarray(_get_model().predict([(premise, claim)]))[0]
    exp = np.exp(logits - logits.max())
    probs = exp / exp.sum()
    return float(probs[_ENTAILMENT_INDEX])


def support_score(evidence: str, claim: str) -> float:
    """How strongly the evidence supports the claim (entailment probability)."""
    return entailment(evidence, claim)
