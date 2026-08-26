from scholarai.domain.models.evaluation import ComponentScores, Recommendation
from scholarai.domain.models.scholarship import RecommendationThresholds, ScoringWeights
from scholarai.domain.services.evaluation import build_evaluation, compute_overall_score

WEIGHTS = ScoringWeights(
    academic_performance=50, eligibility=20, financial_need=10, achievements=10, supporting_evidence=10
)
THRESHOLDS = RecommendationThresholds(highly_recommended_min=85, recommended_min=70, review_required_min=50)


def test_compute_overall_score_is_a_weighted_average():
    scores = ComponentScores(
        academic_performance=100, eligibility=100, financial_need=0, achievements=0, supporting_evidence=100
    )
    # 100*0.5 + 100*0.2 + 0*0.1 + 0*0.1 + 100*0.1 = 80
    assert compute_overall_score(scores, WEIGHTS) == 80.0


def test_scoring_weights_must_sum_to_100():
    import pytest

    with pytest.raises(ValueError, match="must sum to 100"):
        ScoringWeights(
            academic_performance=50, eligibility=50, financial_need=50, achievements=0, supporting_evidence=0
        )


def test_ineligible_forces_ineligible_recommendation_regardless_of_score():
    scores = ComponentScores(
        academic_performance=100, eligibility=100, financial_need=100, achievements=100, supporting_evidence=100
    )
    evaluation = build_evaluation("APP-1", scores, WEIGHTS, THRESHOLDS, eligible=False)
    assert evaluation.recommendation == Recommendation.INELIGIBLE
    assert evaluation.overall_score == 100.0  # score is still reported, just overridden


def test_high_score_classifies_as_highly_recommended():
    scores = ComponentScores(
        academic_performance=100, eligibility=100, financial_need=100, achievements=100, supporting_evidence=100
    )
    evaluation = build_evaluation("APP-1", scores, WEIGHTS, THRESHOLDS, eligible=True)
    assert evaluation.recommendation == Recommendation.HIGHLY_RECOMMENDED


def test_score_near_threshold_boundary_requires_human_review():
    scores = ComponentScores(
        academic_performance=70, eligibility=70, financial_need=70, achievements=70, supporting_evidence=70
    )
    evaluation = build_evaluation("APP-1", scores, WEIGHTS, THRESHOLDS, eligible=True)
    assert evaluation.requires_human_review is True
    assert evaluation.review_reasons


def test_missing_financial_data_adds_explicit_review_reason():
    scores = ComponentScores(
        academic_performance=100, eligibility=100, financial_need=0, achievements=100, supporting_evidence=100
    )
    evaluation = build_evaluation(
        "APP-1", scores, WEIGHTS, THRESHOLDS, eligible=True, extra_review_reasons=("financial information is missing",)
    )
    assert "financial information is missing" in evaluation.review_reasons
    assert evaluation.requires_human_review is True
