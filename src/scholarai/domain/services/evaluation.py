"""Deterministic scoring aggregation and human-review gating.

This is the platform's equivalent of a risk gate: pure arithmetic over the
specialists' component scores plus the configured weights. No LLM is
consulted for the numbers — see ``docs/ARCHITECTURE.md``. The LLM only writes
the natural-language ``summary`` afterward, over these already-final numbers.
"""

from __future__ import annotations

from scholarai.domain.models.evaluation import ComponentScores, EvaluationResult, Recommendation
from scholarai.domain.models.scholarship import RecommendationThresholds, ScoringWeights

UNCERTAINTY_BAND = 5.0
"""Scores within this many points of a threshold boundary are treated as
ambiguous and routed to a human, rather than trusting the tie-break."""


def compute_overall_score(scores: ComponentScores, weights: ScoringWeights) -> float:
    total = (
        scores.academic_performance * weights.academic_performance
        + scores.eligibility * weights.eligibility
        + scores.financial_need * weights.financial_need
        + scores.achievements * weights.achievements
        + scores.supporting_evidence * weights.supporting_evidence
    ) / 100.0
    return round(total, 2)


def _near_a_threshold(score: float, thresholds: RecommendationThresholds) -> bool:
    boundaries = (
        thresholds.highly_recommended_min,
        thresholds.recommended_min,
        thresholds.review_required_min,
    )
    return any(abs(score - boundary) <= UNCERTAINTY_BAND for boundary in boundaries)


def build_evaluation(
    application_id: str,
    scores: ComponentScores,
    weights: ScoringWeights,
    thresholds: RecommendationThresholds,
    eligible: bool,
    extra_review_reasons: tuple[str, ...] = (),
) -> EvaluationResult:
    """Combine component scores into the final, explainable recommendation.

    ``eligible=False`` forces ``INELIGIBLE`` regardless of score — no amount
    of achievement or need can buy back a hard eligibility failure.
    """
    overall = compute_overall_score(scores, weights)
    recommendation = Recommendation.INELIGIBLE if not eligible else thresholds.classify(overall)

    review_reasons = list(extra_review_reasons)
    if eligible and _near_a_threshold(overall, thresholds):
        review_reasons.append(
            f"overall score {overall:.1f} falls within {UNCERTAINTY_BAND:.0f} points of a decision threshold"
        )
    if recommendation is Recommendation.REVIEW_REQUIRED:
        review_reasons.append("score falls in the review-required band")

    requires_human_review = bool(review_reasons) or recommendation in (Recommendation.REVIEW_REQUIRED,)

    return EvaluationResult(
        application_id=application_id,
        component_scores=scores,
        weights_used=weights.as_dict(),
        overall_score=overall,
        recommendation=recommendation,
        requires_human_review=requires_human_review,
        review_reasons=tuple(dict.fromkeys(review_reasons)),
    )
