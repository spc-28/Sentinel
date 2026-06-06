"""Shared helpers for the fake-data tool layer.

Fake data is *deterministic*: values are seeded from their inputs (service,
metric, timestamp, …) via SHA-256, so repeated calls return the same numbers and
a metric's history is stable across calls — which Prophet relies on.
"""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta

# The five services created by scripts/seed.py. Generators work for any service
# name, but these are the known demo set.
KNOWN_SERVICES: tuple[str, ...] = (
    "checkout-api",
    "auth-service",
    "search-api",
    "notifications-worker",
    "inventory-service",
)


def seed_int(*parts: object) -> int:
    """A stable (cross-process) integer seed derived from the given parts."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(digest[:16], 16)


def rng(*parts: object) -> random.Random:
    """A deterministic Random seeded from the given parts."""
    return random.Random(seed_int(*parts))


def now() -> datetime:
    return datetime.now(UTC)


def floor_minute(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


def minute_range(last_n_minutes: int, *, end: datetime | None = None) -> list[datetime]:
    """Per-minute timestamps covering the last ``last_n_minutes`` (ascending)."""
    end_minute = floor_minute(end or now())
    return [end_minute - timedelta(minutes=m) for m in range(last_n_minutes - 1, -1, -1)]
