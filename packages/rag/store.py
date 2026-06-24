"""Qdrant-backed vector store with two collections: runbooks and logs."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient, models

from packages.core.config import get_settings
from packages.rag.embeddings import EMBED_DIM

log = structlog.get_logger()

RUNBOOKS = "runbooks"
LOGS = "logs"
_NAMESPACE = uuid.UUID("3f2b7c9e-0d1a-4c8b-9e2f-1a2b3c4d5e6f")

_client: AsyncQdrantClient | None = None


def client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=get_settings().qdrant_url)
    return _client


def point_id(text: str) -> str:
    """Deterministic id from text, so re-ingesting the same text dedups."""
    return str(uuid.uuid5(_NAMESPACE, text))


async def ensure_collection(name: str) -> None:
    if not await client().collection_exists(name):
        await client().create_collection(
            name,
            vectors_config=models.VectorParams(size=EMBED_DIM, distance=models.Distance.COSINE),
        )


async def upsert(name: str, points: list[tuple[str, list[float], dict[str, Any]]]) -> None:
    if not points:
        return
    await ensure_collection(name)
    await client().upsert(
        name,
        points=[models.PointStruct(id=pid, vector=vec, payload=pl) for pid, vec, pl in points],
    )


async def existing_ids(name: str, ids: list[str]) -> set[str]:
    """Which of ``ids`` are already stored (used to skip re-embedding)."""
    if not await client().collection_exists(name):
        return set()
    found = await client().retrieve(name, ids=ids, with_payload=False, with_vectors=False)
    return {str(record.id) for record in found}


async def search(
    name: str, vector: list[float], *, limit: int = 5
) -> list[tuple[dict[str, Any], float]]:
    if not await client().collection_exists(name):
        return []
    hits = await client().query_points(name, query=vector, limit=limit, with_payload=True)
    return [(dict(h.payload or {}), float(h.score)) for h in hits.points]


async def scroll_payloads(name: str, *, limit: int = 1000) -> list[dict[str, Any]]:
    if not await client().collection_exists(name):
        return []
    records, _ = await client().scroll(name, limit=limit, with_payload=True, with_vectors=False)
    return [dict(r.payload or {}) for r in records]


async def prune_older_than(name: str, cutoff_epoch: float) -> None:
    if not await client().collection_exists(name):
        return
    await client().delete(
        name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="ts", range=models.Range(lt=cutoff_epoch))]
            )
        ),
    )


async def count(name: str) -> int:
    if not await client().collection_exists(name):
        return 0
    return int((await client().count(name)).count)


async def close() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
