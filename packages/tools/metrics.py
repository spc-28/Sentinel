"""Metric tools — time series, p95 latency, and anomaly detection.

Values are deterministic functions of (service, metric, timestamp) with a diurnal
shape, noise and rare spikes. ``is_anomaly`` learns "normal" with Prophet (falling
back to a z-score if Prophet is unavailable).
"""

from __future__ import annotations

import logging
import math
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from pydantic import BaseModel

from packages.tools.common import floor_minute, minute_range, now, rng


@dataclass(frozen=True)
class _Profile:
    base: float
    amplitude: float
    noise: float
    unit: str
    floor: float = 0.0
    ceiling: float | None = None


_PROFILES: dict[str, _Profile] = {
    "latency_ms": _Profile(base=120, amplitude=40, noise=15, unit="ms"),
    "error_rate": _Profile(base=0.012, amplitude=0.006, noise=0.003, unit="ratio"),
    "requests_per_min": _Profile(base=800, amplitude=400, noise=60, unit="rpm"),
    "cpu_percent": _Profile(base=45, amplitude=20, noise=8, unit="percent", ceiling=100),
}
_DEFAULT_PROFILE = _Profile(base=100, amplitude=30, noise=10, unit="value")

# How much a real incident inflates the *recent* value (history stays normal, so
# the elevated recent window reads as a clear anomaly).
_INCIDENT_MULTIPLIER = 3.5


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class MetricSeries(BaseModel):
    service: str
    metric: str
    unit: str
    points: list[MetricPoint]


class LatencySummary(BaseModel):
    service: str
    window_minutes: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    sample_count: int


class AnomalyResult(BaseModel):
    service: str
    metric: str
    is_anomaly: bool
    actual: float
    expected: float
    lower: float
    upper: float
    method: str


def _service_factor(service: str) -> float:
    return rng("svc", service).uniform(0.7, 1.4)


def _metric_value(service: str, metric: str, ts: datetime, incident: bool = False) -> float:
    """Deterministic metric value for one timestamp (diurnal + noise + rare spike)."""
    profile = _PROFILES.get(metric, _DEFAULT_PROFILE)
    base = profile.base * _service_factor(service)
    hour = ts.hour + ts.minute / 60.0
    diurnal = math.sin((hour - 6.0) / 24.0 * 2.0 * math.pi)  # trough at night, peak midday
    r = rng("metric", service, metric, ts.isoformat())
    value = base + profile.amplitude * diurnal + r.gauss(0, profile.noise)
    if r.random() < 0.02:  # rare spike → fuel for anomaly detection
        value *= r.uniform(2.0, 4.0)
    if incident:
        value *= _INCIDENT_MULTIPLIER
    value = max(profile.floor, value)
    if profile.ceiling is not None:
        value = min(profile.ceiling, value)
    return round(value, 4)


def get_metric(service: str, metric_name: str, last_n_minutes: int = 60) -> MetricSeries:
    """A per-minute time series for ``metric_name`` on ``service``."""
    profile = _PROFILES.get(metric_name, _DEFAULT_PROFILE)
    points = [
        MetricPoint(timestamp=ts, value=_metric_value(service, metric_name, ts))
        for ts in minute_range(last_n_minutes)
    ]
    return MetricSeries(service=service, metric=metric_name, unit=profile.unit, points=points)


def get_p95_latency(
    service: str, last_n_minutes: int = 60, incident: bool = False
) -> LatencySummary:
    """p50/p95/p99 request latency over the window (the slowest 5% is p95)."""
    samples: list[float] = []
    for minute in minute_range(last_n_minutes):
        centre = _metric_value(service, "latency_ms", minute, incident)
        r = rng("latency-samples", service, minute.isoformat())
        samples.extend(max(1.0, r.gauss(centre, centre * 0.25)) for _ in range(r.randint(20, 60)))
    arr = np.array(samples)
    return LatencySummary(
        service=service,
        window_minutes=last_n_minutes,
        p50_ms=round(float(np.percentile(arr, 50)), 2),
        p95_ms=round(float(np.percentile(arr, 95)), 2),
        p99_ms=round(float(np.percentile(arr, 99)), 2),
        sample_count=len(samples),
    )


def _history(service: str, metric: str, *, days: int = 14) -> tuple[list[datetime], list[float]]:
    """Hourly values over the past ``days`` (for fitting the 'normal' model)."""
    end = floor_minute(now()).replace(minute=0)
    stamps = [end - timedelta(hours=h) for h in range(days * 24, 0, -1)]
    return stamps, [_metric_value(service, metric, ts) for ts in stamps]


def is_anomaly(
    service: str, metric_name: str, last_n_minutes: int = 30, incident: bool = False
) -> AnomalyResult:
    """Is the recent value of ``metric_name`` unusual versus learned normal?"""
    recent = [
        _metric_value(service, metric_name, ts, incident) for ts in minute_range(last_n_minutes)
    ]
    actual = round(float(np.mean(recent)), 4)
    stamps, values = _history(service, metric_name)  # history stays normal (no incident)

    try:
        expected, lower, upper = _prophet_interval(stamps, values)
        method = "prophet"
    except Exception:  # noqa: BLE001 - any Prophet failure falls back to z-score
        mean = float(np.mean(values))
        std = float(np.std(values)) or 1.0
        expected, lower, upper = mean, mean - 3 * std, mean + 3 * std
        method = "zscore"

    return AnomalyResult(
        service=service,
        metric=metric_name,
        is_anomaly=actual < lower or actual > upper,
        actual=actual,
        expected=round(expected, 4),
        lower=round(lower, 4),
        upper=round(upper, 4),
        method=method,
    )


def _prophet_interval(stamps: list[datetime], values: list[float]) -> tuple[float, float, float]:
    """Fit Prophet on history and return (expected, lower, upper) for the latest point."""
    import pandas as pd
    from prophet import Prophet

    logging.getLogger("prophet").setLevel(logging.ERROR)
    logging.getLogger("cmdstanpy").disabled = True

    df = pd.DataFrame({"ds": [s.replace(tzinfo=None) for s in stamps], "y": values})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = Prophet(daily_seasonality=True, weekly_seasonality=True, interval_width=0.99)
        model.fit(df)
        forecast = model.predict(df.tail(1)[["ds"]])

    row = forecast.iloc[0]
    return float(row["yhat"]), float(row["yhat_lower"]), float(row["yhat_upper"])
