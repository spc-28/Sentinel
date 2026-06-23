"""Embed runbooks from Postgres into the Qdrant 'runbooks' collection.

Idempotent: chunk ids are deterministic and already-stored chunks are skipped, so
re-running never re-embeds unchanged text. Run with: `make ingest-runbooks`.
"""

from __future__ import annotations

import asyncio
import re

import structlog
from packages.core.db import session_factory
from packages.core.logging import configure_logging
from packages.core.repositories import RunbookRepository
from packages.rag import store
from packages.rag.embeddings import embed

log = structlog.get_logger()

_CHUNK_SIZE = 280


def chunk(text: str) -> list[str]:
    text = text.strip()
    if len(text) <= _CHUNK_SIZE:
        return [text]
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if len(current) + len(sentence) <= _CHUNK_SIZE:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks or [text]


async def ingest() -> int:
    async with session_factory() as session:
        runbooks = await RunbookRepository(session).list(limit=1000)

    points: list[tuple[str, str, dict[str, object]]] = []
    for runbook in runbooks:
        for piece in chunk(runbook.content):
            chunk_id = store.point_id(f"{runbook.id}:{piece}")
            # Prefix the title so keyword (BM25) and the reranker can match on it too.
            indexed = f"{runbook.title}. {piece}"
            points.append(
                (
                    chunk_id,
                    indexed,
                    {
                        "runbook_id": str(runbook.id),
                        "title": runbook.title,
                        "content": indexed,
                        "full": runbook.content,
                        "chunk_id": chunk_id,
                    },
                )
            )

    await store.ensure_collection(store.RUNBOOKS)
    already = await store.existing_ids(store.RUNBOOKS, [p[0] for p in points])
    fresh = [p for p in points if p[0] not in already]
    vectors = embed([text for _, text, _ in fresh])
    await store.upsert(
        store.RUNBOOKS,
        [(pid, vec, payload) for (pid, _, payload), vec in zip(fresh, vectors, strict=True)],
    )
    await store.close()
    log.info("runbooks.ingested", chunks=len(fresh), skipped=len(points) - len(fresh))
    return len(fresh)


async def main() -> None:
    configure_logging()
    await ingest()


if __name__ == "__main__":
    asyncio.run(main())
