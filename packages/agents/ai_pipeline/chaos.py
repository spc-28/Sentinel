"""Chaos fault injection for AI-pipeline detectors (state kept in Redis).

Chaos scripts inject a fault against a target (index or service); detectors read
the flag and produce the corresponding degraded signal. Because the harness knows
the injected fault, every chaos scenario doubles as an eval case.
"""

from __future__ import annotations

import redis.asyncio as redis

from packages.core.config import get_settings

FAULTS = ("embedding_drift", "search_quality", "prompt_regression", "cost_spike")


def _key(fault: str, target: str) -> str:
    return f"sentinel:chaos:{fault}:{target}"


def _client() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


async def inject(fault: str, target: str) -> None:
    client = _client()
    await client.set(_key(fault, target), "1")
    await client.aclose()


async def clear(fault: str, target: str) -> None:
    client = _client()
    await client.delete(_key(fault, target))
    await client.aclose()


async def active(fault: str, target: str) -> bool:
    client = _client()
    try:
        return await client.get(_key(fault, target)) == "1"
    finally:
        await client.aclose()


async def clear_all() -> int:
    client = _client()
    keys = [key async for key in client.scan_iter("sentinel:chaos:*")]
    if keys:
        await client.delete(*keys)
    await client.aclose()
    return len(keys)
