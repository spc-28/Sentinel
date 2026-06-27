"""Embedding and text-similarity helpers shared by recall, weighting and merging.

Embeddings are best-effort: if the (heavy) embedding model isn't importable, we
fall back to lexical token overlap, mirroring the RAG-optional pattern used
elsewhere in the codebase. Vectors are short (768-d) and the candidate pool is
small, so cosine is computed in plain Python — no numpy dependency here.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

import structlog

log = structlog.get_logger()

_TOKEN = re.compile(r"[a-z0-9]+")


def embed_text(text: str) -> list[float] | None:
    try:
        from packages.rag.embeddings import embed_one

        return embed_one(text)
    except Exception as exc:  # noqa: BLE001 - embeddings optional
        log.warning("memory.embed_unavailable", error=str(exc))
        return None


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if len(t) > 2}


def lexical(a: str, b: str) -> float:
    """Jaccard token overlap — the fallback when embeddings are unavailable."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def text_similarity(a: str, b: str) -> float:
    """Cosine over embeddings when available, else lexical overlap (0..1)."""
    va, vb = embed_text(a), embed_text(b)
    if va is not None and vb is not None:
        return cosine(va, vb)
    return lexical(a, b)
