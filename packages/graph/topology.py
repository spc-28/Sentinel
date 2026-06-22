"""Canonical fake dependency topology for the 5 seeded services + infra nodes.

Each tuple is (source, target, kind): source DEPENDS_ON target. Used to seed the
graph so it works without real traces.
"""

from __future__ import annotations

from typing import Final

TOPOLOGY: Final[list[tuple[str, str, str]]] = [
    ("checkout-api", "auth-service", "CALLS"),
    ("checkout-api", "inventory-service", "CALLS"),
    ("checkout-api", "payments-gateway", "CALLS"),
    ("checkout-api", "postgres", "READS_FROM"),
    ("checkout-api", "redis", "READS_FROM"),
    ("search-api", "inventory-service", "CALLS"),
    ("search-api", "postgres", "READS_FROM"),
    ("search-api", "redis", "READS_FROM"),
    ("notifications-worker", "auth-service", "CALLS"),
    ("notifications-worker", "postgres", "READS_FROM"),
    ("auth-service", "postgres", "READS_FROM"),
    ("auth-service", "redis", "READS_FROM"),
    ("inventory-service", "postgres", "READS_FROM"),
]

# Maps a trace span's operation name to a (target, kind) edge, for build_from_traces.
SPAN_TARGETS: Final[dict[str, tuple[str, str]]] = {
    "auth.verify_token": ("auth-service", "CALLS"),
    "http.call inventory": ("inventory-service", "CALLS"),
    "http.call payments": ("payments-gateway", "CALLS"),
    "db.query": ("postgres", "READS_FROM"),
    "redis.get": ("redis", "READS_FROM"),
}
