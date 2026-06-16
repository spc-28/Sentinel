"""Shared graph state passed between the five agent nodes.

The five nodes read and update one ``GraphState``. ``evidence`` accumulates across
nodes (and across investigator retries) via an additive reducer; other fields are
replaced by whichever node writes them.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str  # logs | metrics | traces | deploys
    summary: str
    detail: str | None = None


class HypothesisItem(BaseModel):
    statement: str
    description: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1, le=5)


class VerifiedHypothesis(BaseModel):
    statement: str
    description: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1, le=5)
    support_score: float = Field(ge=0.0, le=1.0)
    verdict: str  # supported | inconclusive | unsupported


class ReportDoc(BaseModel):
    root_cause: str
    timeline: list[str]
    evidence: list[str]
    suggested_fix: str
    markdown: str


class GraphState(TypedDict, total=False):
    alert: dict[str, Any]
    is_real: bool
    detector_notes: str
    evidence: Annotated[list[EvidenceItem], operator.add]
    investigator_rounds: int
    hypotheses: list[HypothesisItem]
    verified: list[VerifiedHypothesis]
    verify_attempts: int
    report: ReportDoc | None


def initial_state(alert: dict[str, Any]) -> GraphState:
    return GraphState(
        alert=alert,
        is_real=True,
        detector_notes="",
        evidence=[],
        investigator_rounds=0,
        hypotheses=[],
        verified=[],
        verify_attempts=0,
        report=None,
    )
