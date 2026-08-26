"""The combined evaluation, the Critic's review of it, and the final verdict.

Scoring itself is deterministic Python (see
``domain.services.scoring``) — the LLM is only used afterward to explain the
numbers in plain language. See ``docs/ARCHITECTURE.md`` §Deterministic vs LLM.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from scholarai.domain.models.explainability import Evidence


class Recommendation(StrEnum):
    HIGHLY_RECOMMENDED = "highly_recommended"
    RECOMMENDED = "recommended"
    REVIEW_REQUIRED = "review_required"
    NOT_RECOMMENDED = "not_recommended"
    INELIGIBLE = "ineligible"


class ComponentScores(BaseModel):
    """The five weighted inputs to the overall score, each 0-100."""

    model_config = ConfigDict(frozen=True)

    academic_performance: float = Field(ge=0.0, le=100.0)
    eligibility: float = Field(ge=0.0, le=100.0)
    financial_need: float = Field(ge=0.0, le=100.0)
    achievements: float = Field(ge=0.0, le=100.0)
    supporting_evidence: float = Field(ge=0.0, le=100.0)


class EvaluationResult(BaseModel):
    """The Evaluation Agent's combined, deterministic scoring output."""

    model_config = ConfigDict(frozen=True)

    application_id: str
    component_scores: ComponentScores
    weights_used: dict[str, float]
    overall_score: float = Field(ge=0.0, le=100.0)
    recommendation: Recommendation
    summary: str = ""
    requires_human_review: bool = False
    review_reasons: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()


class CriticVerdict(StrEnum):
    PASS = "pass"
    REVISE = "revise"


class CriticResult(BaseModel):
    """The Critic Agent's independent audit of an ``EvaluationResult``."""

    model_config = ConfigDict(frozen=True)

    verdict: CriticVerdict
    issues: tuple[str, ...] = ()
    checked: tuple[str, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
