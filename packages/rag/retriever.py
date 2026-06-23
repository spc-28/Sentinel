"""Hybrid retrieval: BM25 keyword + semantic search, fused and cross-encoder reranked.

Runbooks are indexed as chunks (summarize-then-drill-in): search finds the best
chunk, then we return its parent runbook. Keyword and semantic rankings are merged
with reciprocal rank fusion, then a cross-encoder reranks the top candidates.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

from packages.rag import store
from packages.rag.embeddings import embed_one

log = structlog.get_logger()

_RRF_K = 60
_CANDIDATES = 20
_RERANK_TOP = 10
_reranker: Any = None


class RunbookHit(BaseModel):
    runbook_id: str
    title: str
    content: str
    score: float


class LogHit(BaseModel):
    service: str
    message: str
    score: float


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _get_reranker() -> Any:
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder  # heavy: torch

        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def _rrf(rankings: list[list[dict[str, Any]]], key: str) -> dict[str, float]:
    """Reciprocal rank fusion: sum 1/(k+rank) across rankings, keyed by payload[key]."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, payload in enumerate(ranking):
            scores[payload[key]] = scores.get(payload[key], 0.0) + 1.0 / (_RRF_K + rank)
    return scores


async def search_runbooks(query: str, top_k: int = 3) -> list[RunbookHit]:
    chunks = await store.scroll_payloads(store.RUNBOOKS)
    if not chunks:
        return []
    by_id = {c["chunk_id"]: c for c in chunks}

    semantic = [
        p for p, _ in await store.search(store.RUNBOOKS, embed_one(query), limit=_CANDIDATES)
    ]

    bm25 = BM25Okapi([_tokenize(c["content"]) for c in chunks])
    order = sorted(
        range(len(chunks)), key=lambda i: bm25.get_scores(_tokenize(query))[i], reverse=True
    )
    keyword = [chunks[i] for i in order[:_CANDIDATES]]

    fused = _rrf([semantic, keyword], key="chunk_id")
    candidates = [by_id[cid] for cid in sorted(fused, key=lambda c: fused[c], reverse=True)]
    candidates = candidates[:_RERANK_TOP]

    scores = _get_reranker().predict([(query, c["content"]) for c in candidates])
    ranked = sorted(zip(candidates, scores, strict=True), key=lambda cs: cs[1], reverse=True)

    hits: list[RunbookHit] = []
    seen: set[str] = set()
    for chunk, score in ranked:  # dedup chunks to their parent runbook
        if chunk["runbook_id"] in seen:
            continue
        seen.add(chunk["runbook_id"])
        hits.append(
            RunbookHit(
                runbook_id=chunk["runbook_id"],
                title=chunk["title"],
                content=chunk["full"],
                score=float(score),
            )
        )
        if len(hits) >= top_k:
            break
    return hits


async def search_logs(query: str, top_k: int = 5) -> list[LogHit]:
    results = await store.search(store.LOGS, embed_one(query), limit=top_k)
    return [
        LogHit(service=p.get("service", "unknown"), message=p.get("message", ""), score=score)
        for p, score in results
    ]
