"""Log tools — search, recent errors, and a compact summary.

Fake logs are generated per service/minute with a 1–3% error rate. ``summarize_logs``
returns aggregate stats (not raw lines) so an agent isn't flooded with data.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from packages.tools.common import floor_minute, minute_range, rng

# Realistic message templates per level. ERROR templates double as "error types".
_INFO_MESSAGES = (
    "request completed",
    "cache hit",
    "user session refreshed",
    "background task finished",
    "health check ok",
)
_WARN_MESSAGES = (
    "slow downstream response",
    "retrying request",
    "cache miss",
    "connection pool near capacity",
)
_ERROR_MESSAGES = (
    "database connection timeout",
    "upstream 503 from payment provider",
    "unhandled exception in request handler",
    "redis command timed out",
    "null pointer in serializer",
    "request deadline exceeded",
)


class LogLevel(StrEnum):
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"


class LogEntry(BaseModel):
    timestamp: datetime
    service: str
    level: LogLevel
    message: str
    trace_id: str | None = None
    status_code: int | None = None


class ErrorCount(BaseModel):
    message: str
    count: int


class TimeBucket(BaseModel):
    start: datetime
    total: int
    errors: int


class LogSummary(BaseModel):
    service: str
    window_minutes: int
    total: int
    by_level: dict[str, int]
    error_rate: float
    top_errors: list[ErrorCount]
    buckets: list[TimeBucket]


def _entries_for_minute(service: str, minute: datetime) -> list[LogEntry]:
    """Deterministic log lines for one service-minute (1–3% are errors)."""
    r = rng("logs", service, minute.isoformat())
    count = r.randint(8, 40)
    error_rate = r.uniform(0.01, 0.03)
    entries: list[LogEntry] = []
    for _ in range(count):
        roll = r.random()
        if roll < error_rate:
            level = LogLevel.error
            message = r.choice(_ERROR_MESSAGES)
            status_code = r.choice((500, 502, 503, 504))
        elif roll < error_rate + 0.10:
            level = LogLevel.warning
            message = r.choice(_WARN_MESSAGES)
            status_code = r.choice((200, 429))
        else:
            level = LogLevel.info
            message = r.choice(_INFO_MESSAGES)
            status_code = 200
        entries.append(
            LogEntry(
                timestamp=minute.replace(second=r.randint(0, 59)),
                service=service,
                level=level,
                message=message,
                trace_id=f"{r.getrandbits(64):016x}",
                status_code=status_code,
            )
        )
    entries.sort(key=lambda e: e.timestamp)
    return entries


def _window_entries(service: str, last_n_minutes: int) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for minute in minute_range(last_n_minutes):
        entries.extend(_entries_for_minute(service, minute))
    return entries


def search_logs(service: str, last_n_minutes: int = 60, search_text: str = "") -> list[LogEntry]:
    """Return log entries for ``service`` whose message contains ``search_text``."""
    needle = search_text.lower()
    return [e for e in _window_entries(service, last_n_minutes) if needle in e.message.lower()]


def get_recent_errors(service: str, limit: int = 20) -> list[LogEntry]:
    """The most recent ERROR-level logs for ``service`` (last 6h, newest first)."""
    errors = [e for e in _window_entries(service, 360) if e.level is LogLevel.error]
    errors.sort(key=lambda e: e.timestamp, reverse=True)
    return errors[:limit]


def summarize_logs(service: str, last_n_minutes: int = 60) -> LogSummary:
    """Aggregate stats for a service's logs — counts, error rate, top errors, buckets."""
    entries = _window_entries(service, last_n_minutes)
    total = len(entries)
    by_level = Counter(e.level.value for e in entries)
    error_total = by_level.get(LogLevel.error.value, 0)
    top = Counter(e.message for e in entries if e.level is LogLevel.error)

    bucket_minutes = max(1, last_n_minutes // 12)
    buckets: dict[datetime, list[int]] = {}
    for e in entries:
        anchor = floor_minute(e.timestamp)
        key = anchor.replace(minute=(anchor.minute // bucket_minutes) * bucket_minutes)
        slot = buckets.setdefault(key, [0, 0])
        slot[0] += 1
        if e.level is LogLevel.error:
            slot[1] += 1

    return LogSummary(
        service=service,
        window_minutes=last_n_minutes,
        total=total,
        by_level=dict(by_level),
        error_rate=round(error_total / total, 4) if total else 0.0,
        top_errors=[ErrorCount(message=m, count=c) for m, c in top.most_common(5)],
        buckets=[
            TimeBucket(start=start, total=t, errors=err)
            for start, (t, err) in sorted(buckets.items())
        ],
    )
