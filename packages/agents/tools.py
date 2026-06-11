"""Part 3 tool functions wrapped as LangChain tools.

Each wrapper returns a compact JSON string (lists are capped) so the model gets
predictable, token-bounded observations.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from packages.tools import deploys, logs, metrics, traces

_MAX_ITEMS = 15


def _json(payload: Any) -> str:
    return json.dumps(payload, default=str)


@tool
def search_logs(service: str, last_n_minutes: int = 60, search_text: str = "") -> str:
    """Search a service's logs for entries whose message contains search_text."""
    found = logs.search_logs(service, last_n_minutes, search_text)
    return _json(
        {"count": len(found), "sample": [e.model_dump(mode="json") for e in found[:_MAX_ITEMS]]}
    )


@tool
def get_recent_errors(service: str, limit: int = 10) -> str:
    """Return the most recent ERROR-level logs for a service."""
    errors = logs.get_recent_errors(service, limit)
    return _json([e.model_dump(mode="json") for e in errors])


@tool
def summarize_logs(service: str, last_n_minutes: int = 60) -> str:
    """Aggregate log stats for a service: counts by level, error rate, top errors."""
    return logs.summarize_logs(service, last_n_minutes).model_dump_json()


@tool
def get_metric(service: str, metric_name: str, last_n_minutes: int = 60) -> str:
    """Summary stats (min/max/avg/last) of a metric time series for a service.

    metric_name is one of: latency_ms, error_rate, requests_per_min, cpu_percent.
    """
    series = metrics.get_metric(service, metric_name, last_n_minutes)
    values = [p.value for p in series.points]
    if not values:
        return _json({"metric": metric_name, "unit": series.unit, "points": 0})
    return _json(
        {
            "metric": metric_name,
            "unit": series.unit,
            "points": len(values),
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 4),
            "last": values[-1],
        }
    )


@tool
def get_p95_latency(service: str, last_n_minutes: int = 60) -> str:
    """Return p50/p95/p99 request latency (ms) for a service over the window."""
    return metrics.get_p95_latency(service, last_n_minutes).model_dump_json()


@tool
def is_anomaly(service: str, metric_name: str, last_n_minutes: int = 30) -> str:
    """Check whether a metric's recent value is anomalous vs learned normal."""
    return metrics.is_anomaly(service, metric_name, last_n_minutes).model_dump_json()


@tool
def get_trace(trace_id: str) -> str:
    """Return the full span breakdown for a single trace id."""
    return traces.get_trace(trace_id).model_dump_json()


@tool
def find_slow_traces(service: str, slower_than_ms: float = 500, last_n_minutes: int = 60) -> str:
    """Find traces for a service slower than slower_than_ms (slowest first)."""
    found = traces.find_slow_traces(service, slower_than_ms, last_n_minutes)
    return _json(
        {"count": len(found), "sample": [t.model_dump(mode="json") for t in found[:_MAX_ITEMS]]}
    )


@tool
def find_error_traces(service: str, last_n_minutes: int = 60) -> str:
    """Find errored traces for a service (newest first)."""
    found = traces.find_error_traces(service, last_n_minutes)
    return _json(
        {"count": len(found), "sample": [t.model_dump(mode="json") for t in found[:_MAX_ITEMS]]}
    )


@tool
def recent_deploys(service: str, last_n_minutes: int = 1440) -> str:
    """List recent deploys for a service (newest first)."""
    found = deploys.recent_deploys(service, last_n_minutes)
    return _json([d.model_dump(mode="json") for d in found[:_MAX_ITEMS]])


@tool
def get_deploy_changes(deploy_id: str) -> str:
    """Return the files changed in a deploy (deploy_id from recent_deploys)."""
    return deploys.get_deploy_changes(deploy_id).model_dump_json()


@tool
def draft_revert(deploy_id: str) -> str:
    """Draft a revert PR suggestion for a deploy (suggestion only, never reverts)."""
    return deploys.draft_revert(deploy_id).model_dump_json()


ALL_TOOLS = [
    search_logs,
    get_recent_errors,
    summarize_logs,
    get_metric,
    get_p95_latency,
    is_anomaly,
    get_trace,
    find_slow_traces,
    find_error_traces,
    recent_deploys,
    get_deploy_changes,
    draft_revert,
]
