"""Built-in scholarship presets, selectable by code from the API/UI/CLI.

Mirrors the reference project's ``strategy_presets.py`` — a small, explicit
registry rather than a database table, because these change rarely and
belong in version control next to the tests that pin their behaviour.
"""

from __future__ import annotations

from scholarai.domain.models.scholarship import (
    EligibilityRequirements,
    RecommendationThresholds,
    ScholarshipPreset,
    ScoringWeights,
)

MERIT_SCHOLARSHIP = ScholarshipPreset(
    code="merit_scholarship",
    name="Academic Merit Scholarship",
    description="Awarded primarily on sustained academic excellence.",
    requirements=EligibilityRequirements(
        min_cgpa=3.5,
        min_credits_completed=30,
        min_semester=2,
        max_failed_courses=0,
        required_documents=("transcript",),
        disciplinary_clean_required=True,
    ),
    weights=ScoringWeights(
        academic_performance=50.0,
        eligibility=20.0,
        financial_need=10.0,
        achievements=10.0,
        supporting_evidence=10.0,
    ),
    thresholds=RecommendationThresholds(highly_recommended_min=88.0, recommended_min=72.0, review_required_min=55.0),
)

NEED_BASED_SCHOLARSHIP = ScholarshipPreset(
    code="need_based_scholarship",
    name="Financial Need-Based Scholarship",
    description="Awarded primarily on demonstrated financial need, with a baseline academic bar.",
    requirements=EligibilityRequirements(
        min_cgpa=2.5,
        min_credits_completed=15,
        min_semester=1,
        max_failed_courses=2,
        required_documents=("transcript", "financial_statement"),
        disciplinary_clean_required=True,
    ),
    weights=ScoringWeights(
        academic_performance=20.0,
        eligibility=15.0,
        financial_need=45.0,
        achievements=10.0,
        supporting_evidence=10.0,
    ),
    thresholds=RecommendationThresholds(highly_recommended_min=82.0, recommended_min=65.0, review_required_min=45.0),
)

LEADERSHIP_SCHOLARSHIP = ScholarshipPreset(
    code="leadership_scholarship",
    name="Leadership & Community Impact Scholarship",
    description="Awarded for leadership, volunteering, and community contribution alongside a solid academic record.",
    requirements=EligibilityRequirements(
        min_cgpa=3.0,
        min_credits_completed=30,
        min_semester=2,
        max_failed_courses=1,
        required_documents=("transcript", "recommendation_letter"),
        disciplinary_clean_required=True,
    ),
    weights=ScoringWeights(
        academic_performance=25.0,
        eligibility=15.0,
        financial_need=10.0,
        achievements=40.0,
        supporting_evidence=10.0,
    ),
    thresholds=RecommendationThresholds(highly_recommended_min=85.0, recommended_min=68.0, review_required_min=50.0),
)

PRESETS: dict[str, ScholarshipPreset] = {
    preset.code: preset for preset in (MERIT_SCHOLARSHIP, NEED_BASED_SCHOLARSHIP, LEADERSHIP_SCHOLARSHIP)
}


def get_preset(code: str) -> ScholarshipPreset:
    try:
        return PRESETS[code]
    except KeyError as exc:
        available = ", ".join(sorted(PRESETS))
        msg = f"unknown scholarship code {code!r}; available: {available}"
        raise ValueError(msg) from exc
