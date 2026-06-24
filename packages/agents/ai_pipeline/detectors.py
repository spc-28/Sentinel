"""AI-system failure detectors — the differentiating checks.

Each detector runs a real algorithm (Wasserstein distance, NLI faithfulness,
z-score) over simulated signals. A chaos flag (see ``chaos``) perturbs the signal,
so injected faults are actually detected — and known at injection time (free evals).
"""

from __future__ import annotations

from typing import cast

import numpy as np
import structlog
from scipy.stats import wasserstein_distance

from packages.agents.ai_pipeline import chaos
from packages.agents.ai_pipeline.schemas import (
    CostResult,
    DriftResult,
    IndexHealthResult,
    PromptRegressionResult,
    RagQualityResult,
)
from packages.core.config import get_settings
from packages.tools.common import seed_int

_DIM = 768


# --- embedding drift -----------------------------------------------------
def _unit(vector: np.ndarray) -> np.ndarray:
    return cast("np.ndarray", vector / (np.linalg.norm(vector) + 1e-9))


def _sample_vectors(index: str, tag: str, n: int, shift: float) -> np.ndarray:
    rng = np.random.default_rng(seed_int("aivec", index, tag))
    base = _unit(np.random.default_rng(seed_int("aibase", index)).normal(size=_DIM))
    drift = _unit(np.random.default_rng(seed_int("aidrift", index)).normal(size=_DIM))
    # Per-vector noise must stay small in 768-D or it swamps the drift signal.
    points = base + shift * drift + rng.normal(scale=0.03, size=(n, _DIM))
    return points / (np.linalg.norm(points, axis=1, keepdims=True) + 1e-9)


async def check_embedding_drift(index_name: str, last_n_hours: int = 24) -> DriftResult:
    """Compare recent understanding-vectors to a baseline via Wasserstein distance."""
    threshold = get_settings().drift_wasserstein_threshold
    drifted = await chaos.active("embedding_drift", index_name)

    baseline = _sample_vectors(index_name, "baseline", 200, shift=0.0)
    recent = _sample_vectors(
        index_name, f"recent-{last_n_hours}", 200, shift=0.7 if drifted else 0.0
    )

    centroid = _unit(baseline.mean(axis=0))
    distance = float(wasserstein_distance(baseline @ centroid, recent @ centroid))
    detected = distance > threshold
    note = (
        "Recent vectors diverged from baseline — likely an embedding-model change; "
        "rebuild the index."
        if detected
        else "Vector distribution stable versus baseline."
    )
    return DriftResult(
        index=index_name,
        drift_detected=detected,
        wasserstein=round(distance, 4),
        threshold=threshold,
        baseline_size=len(baseline),
        recent_size=len(recent),
        note=note,
    )


# --- RAG search-quality drop ---------------------------------------------
_FAITHFUL = [
    (
        "The connection pool was exhausted, causing timeouts.",
        "The pool was exhausted and requests timed out.",
    ),
    (
        "A deploy at 14:00 changed the payment client.",
        "The 14:00 deploy modified the payment client.",
    ),
    ("Disk usage hit 100% and writes failed.", "The disk filled up and writes failed."),
]
_UNFAITHFUL = [
    (
        "The connection pool was exhausted, causing timeouts.",
        "The weather was sunny and unrelated to the outage.",
    ),
    (
        "A deploy at 14:00 changed the payment client.",
        "No deploys happened and the database was fine.",
    ),
    ("Disk usage hit 100% and writes failed.", "Memory was leaking and the network partitioned."),
]


async def check_rag_quality(index_name: str) -> RagQualityResult:
    """Sample answers and score faithfulness against their context with DeBERTa-MNLI."""
    from packages.rag.nli import support_score

    threshold = get_settings().rag_quality_threshold
    degraded_mode = await chaos.active("search_quality", index_name)
    samples = _UNFAITHFUL if degraded_mode else _FAITHFUL

    scores = [support_score(context, answer) for context, answer in samples]
    faithfulness = round(sum(scores) / len(scores), 3)
    degraded = faithfulness < threshold
    note = (
        "RAG answers are not faithful to retrieved context — check retrieval or the model."
        if degraded
        else "RAG answers remain faithful to their context."
    )
    return RagQualityResult(
        index=index_name,
        degraded=degraded,
        faithfulness=faithfulness,
        threshold=threshold,
        sample_size=len(samples),
        note=note,
    )


# --- prompt regression ---------------------------------------------------
async def check_prompt_regression(service: str) -> PromptRegressionResult:
    """When a new prompt version ships, compare its quick-check score to the previous one."""
    regressed_mode = await chaos.active("prompt_regression", service)
    previous_score = 0.86
    current_score = 0.55 if regressed_mode else 0.86
    previous_version = "v3"
    current_version = "v4" if regressed_mode else "v3"
    regressed = (previous_score - current_score) > 0.15
    note = (
        f"New prompt {current_version} scores {current_score} vs {previous_score} for "
        f"{previous_version}; consider reverting."
        if regressed
        else "No new prompt version, or no regression detected."
    )
    return PromptRegressionResult(
        service=service,
        regressed=regressed,
        previous_version=previous_version,
        current_version=current_version,
        previous_score=previous_score,
        current_score=current_score,
        note=note,
    )


# --- cost spike ----------------------------------------------------------
async def get_ai_cost(service: str, last_n_hours: int = 24) -> CostResult:
    """Track hourly AI spend and flag an unusual jump in the most recent hour."""
    ratio = get_settings().cost_spike_ratio
    spiking = await chaos.active("cost_spike", service)

    rng = np.random.default_rng(seed_int("aicost", service))
    base = 2.0 + rng.uniform(0, 1.5)
    hourly = [round(base + rng.normal(scale=0.3), 3) for _ in range(last_n_hours)]
    hourly = [max(0.1, c) for c in hourly]
    if spiking:
        hourly[-1] = round(hourly[-1] * 6.0, 3)

    baseline_avg = float(np.mean(hourly[:-1])) if len(hourly) > 1 else hourly[-1]
    last_hour = hourly[-1]
    spike = last_hour > baseline_avg * ratio
    note = (
        f"Last-hour spend ${last_hour} is >{ratio}x the ${round(baseline_avg, 3)} baseline."
        if spike
        else "AI spend within normal range."
    )
    return CostResult(
        service=service,
        hours=last_n_hours,
        total_usd=round(sum(hourly), 2),
        hourly_usd=hourly,
        spike_detected=spike,
        baseline_avg_usd=round(baseline_avg, 3),
        last_hour_usd=last_hour,
        note=note,
    )


# --- composite index health ----------------------------------------------
async def check_index_health(index_name: str) -> IndexHealthResult:
    """Overall health for a vector index: point count + drift."""
    from packages.rag import store

    points = await store.count(index_name)
    drift = await check_embedding_drift(index_name)
    issues: list[str] = []
    if points == 0:
        issues.append("index is empty")
    if drift.drift_detected:
        issues.append("embedding drift detected")
    return IndexHealthResult(
        index=index_name,
        healthy=not issues,
        points=points,
        drift=drift,
        issues=issues,
    )


log = structlog.get_logger()


async def run_all_detectors(*, indexes: list[str], services: list[str]) -> list[str]:
    """Run every detector once (periodic job); return short descriptions of detections."""
    detections: list[str] = []
    for index in indexes:
        drift = await check_embedding_drift(index)
        if drift.drift_detected:
            detections.append(f"embedding_drift:{index}")
        quality = await check_rag_quality(index)
        if quality.degraded:
            detections.append(f"search_quality:{index}")
    for service in services:
        cost = await get_ai_cost(service)
        if cost.spike_detected:
            detections.append(f"cost_spike:{service}")
        prompt = await check_prompt_regression(service)
        if prompt.regressed:
            detections.append(f"prompt_regression:{service}")
    if detections:
        log.info("ai_pipeline.detections", detections=detections)
    return detections
