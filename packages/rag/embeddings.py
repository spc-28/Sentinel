"""Text → vector embeddings (all-mpnet-base-v2), cached to avoid re-embedding.

The model is loaded lazily on first use (heavy import), so importing this module is
cheap. ``embed_one`` is LRU-cached by text, so identical strings embed once.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
EMBED_DIM = 768

_model: Any = None


def _get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # heavy: torch

        _model = SentenceTransformer(MODEL_NAME)
    return _model


@lru_cache(maxsize=8192)
def _embed_cached(text: str) -> tuple[float, ...]:
    vector = _get_model().encode(text, normalize_embeddings=True)
    return tuple(float(x) for x in vector)


def embed_one(text: str) -> list[float]:
    return list(_embed_cached(text))


def embed(texts: list[str]) -> list[list[float]]:
    return [embed_one(t) for t in texts]
