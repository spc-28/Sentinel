"""Result models for the AI-pipeline detectors."""

from __future__ import annotations

from pydantic import BaseModel


class DriftResult(BaseModel):
    index: str
    drift_detected: bool
    wasserstein: float
    threshold: float
    baseline_size: int
    recent_size: int
    note: str


class RagQualityResult(BaseModel):
    index: str
    degraded: bool
    faithfulness: float
    threshold: float
    sample_size: int
    note: str


class PromptRegressionResult(BaseModel):
    service: str
    regressed: bool
    previous_version: str
    current_version: str
    previous_score: float
    current_score: float
    note: str


class CostResult(BaseModel):
    service: str
    hours: int
    total_usd: float
    hourly_usd: list[float]
    spike_detected: bool
    baseline_avg_usd: float
    last_hour_usd: float
    note: str


class IndexHealthResult(BaseModel):
    index: str
    healthy: bool
    points: int
    drift: DriftResult
    issues: list[str]
