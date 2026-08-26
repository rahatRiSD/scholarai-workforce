"""Scholarship presets: the deterministic policy knobs, not the LLM's to invent.

A scholarship's numeric requirements (minimum CGPA, minimum credits, ...) and
its scoring weights/thresholds are configuration, not prose an LLM has to
re-derive every run. Ambiguous, non-numeric policy language (e.g. "priority
given to first-generation students") is what the Policy/RAG Agent exists for.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholarai.domain.models.evaluation import Recommendation


class EligibilityRequirements(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_cgpa: float = Field(ge=0.0, le=4.0)
    min_credits_completed: int = Field(ge=0)
    min_semester: int = Field(ge=1, default=1)
    max_failed_courses: int = Field(ge=0, default=1)
    required_documents: tuple[str, ...] = ()
    disciplinary_clean_required: bool = True


class ScoringWeights(BaseModel):
    """Must sum to 100 — enforced so a misconfiguration fails loudly, not silently."""

    model_config = ConfigDict(frozen=True)

    academic_performance: float = 40.0
    eligibility: float = 20.0
    financial_need: float = 20.0
    achievements: float = 10.0
    supporting_evidence: float = 10.0

    @model_validator(mode="after")
    def _check_sums_to_100(self) -> ScoringWeights:
        total = (
            self.academic_performance
            + self.eligibility
            + self.financial_need
            + self.achievements
            + self.supporting_evidence
        )
        if abs(total - 100.0) > 0.01:
            msg = f"scoring weights must sum to 100, got {total}"
            raise ValueError(msg)
        return self

    def as_dict(self) -> dict[str, float]:
        return {
            "academic_performance": self.academic_performance,
            "eligibility": self.eligibility,
            "financial_need": self.financial_need,
            "achievements": self.achievements,
            "supporting_evidence": self.supporting_evidence,
        }


class RecommendationThresholds(BaseModel):
    """Score cutoffs mapping to a ``Recommendation`` — configurable, not hard-coded prose."""

    model_config = ConfigDict(frozen=True)

    highly_recommended_min: float = 85.0
    recommended_min: float = 70.0
    review_required_min: float = 50.0
    # below review_required_min -> NOT_RECOMMENDED (unless ineligible, which overrides all)

    def classify(self, score: float) -> Recommendation:
        if score >= self.highly_recommended_min:
            return Recommendation.HIGHLY_RECOMMENDED
        if score >= self.recommended_min:
            return Recommendation.RECOMMENDED
        if score >= self.review_required_min:
            return Recommendation.REVIEW_REQUIRED
        return Recommendation.NOT_RECOMMENDED


class ScholarshipPreset(BaseModel):
    """A named scholarship program with its full deterministic policy."""

    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    description: str
    requirements: EligibilityRequirements
    weights: ScoringWeights = ScoringWeights()
    thresholds: RecommendationThresholds = RecommendationThresholds()
