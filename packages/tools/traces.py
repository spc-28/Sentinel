"""Trace tools — fetch one trace, or find slow / errored traces for a service.

A trace is fully determined by its ``trace_id`` (service, timing, spans), so
``get_trace`` regenerates exactly what the finders summarised.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel

from packages.tools.common import KNOWN_SERVICES, floor_minute, now, rng

_OPERATIONS = (
    "db.query",
    "redis.get",
    "http.call payments",
    "http.call inventory",
    "serialize.response",
    "auth.verify_token",
)
_ERROR_RATE = 0.03


class Span(BaseModel):
    span_id: str
    parent_span_id: str | None
    name: str
    service: str
    start_offset_ms: float
    duration_ms: float
    status: str  # "ok" | "error"


class Trace(BaseModel):
    trace_id: str
    service: str
    start_time: datetime
    duration_ms: float
    status: str
    span_count: int
    spans: list[Span]


class TraceSummary(BaseModel):
    trace_id: str
    service: str
    start_time: datetime
    duration_ms: float
    status: str
    root_operation: str


def _build_trace(trace_id: str) -> Trace:
    """Deterministically reconstruct a full trace from its id."""
    r = rng("trace", trace_id)
    service = r.choice(KNOWN_SERVICES)
    start_time = floor_minute(now()) - timedelta(seconds=r.randint(0, 6 * 3600))
    is_error = r.random() < _ERROR_RATE

    root_op = f"{r.choice(('GET', 'POST'))} /{service.split('-')[0]}"
    root_duration = max(5.0, r.gauss(180, 70)) * (r.uniform(2.0, 5.0) if r.random() < 0.1 else 1.0)

    spans: list[Span] = [
        Span(
            span_id=f"{r.getrandbits(64):016x}",
            parent_span_id=None,
            name=root_op,
            service=service,
            start_offset_ms=0.0,
            duration_ms=round(root_duration, 2),
            status="error" if is_error else "ok",
        )
    ]
    cursor = 2.0
    for _ in range(r.randint(2, 6)):
        dur = max(1.0, r.gauss(root_duration / 5, root_duration / 12))
        child_error = is_error and r.random() < 0.5
        spans.append(
            Span(
                span_id=f"{r.getrandbits(64):016x}",
                parent_span_id=spans[0].span_id,
                name=r.choice(_OPERATIONS),
                service=service,
                start_offset_ms=round(cursor, 2),
                duration_ms=round(dur, 2),
                status="error" if child_error else "ok",
            )
        )
        cursor += dur

    return Trace(
        trace_id=trace_id,
        service=service,
        start_time=start_time,
        duration_ms=round(root_duration, 2),
        status="error" if is_error else "ok",
        span_count=len(spans),
        spans=spans,
    )


def _summary(trace: Trace) -> TraceSummary:
    return TraceSummary(
        trace_id=trace.trace_id,
        service=trace.service,
        start_time=trace.start_time,
        duration_ms=trace.duration_ms,
        status=trace.status,
        root_operation=trace.spans[0].name,
    )


def _candidate_traces(service: str, last_n_minutes: int, *, pool: int = 600) -> list[Trace]:
    """Build a pool of traces and keep those for ``service`` within the window."""
    cutoff = now() - timedelta(minutes=last_n_minutes)
    pool_rng = rng("trace-pool", service)
    traces: list[Trace] = []
    for _ in range(pool):
        trace = _build_trace(f"{pool_rng.getrandbits(128):032x}")
        if trace.service == service and trace.start_time >= cutoff:
            traces.append(trace)
    return traces


def get_trace(trace_id: str) -> Trace:
    """Full detail of a single request by trace id."""
    return _build_trace(trace_id)


def find_slow_traces(
    service: str, slower_than_ms: float = 500, last_n_minutes: int = 60
) -> list[TraceSummary]:
    """Traces for ``service`` slower than ``slower_than_ms`` (slowest first)."""
    slow = [t for t in _candidate_traces(service, last_n_minutes) if t.duration_ms > slower_than_ms]
    slow.sort(key=lambda t: t.duration_ms, reverse=True)
    return [_summary(t) for t in slow]


def find_error_traces(service: str, last_n_minutes: int = 60) -> list[TraceSummary]:
    """Errored traces for ``service`` (newest first)."""
    errored = [t for t in _candidate_traces(service, last_n_minutes) if t.status == "error"]
    errored.sort(key=lambda t: t.start_time, reverse=True)
    return [_summary(t) for t in errored]
