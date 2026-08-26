"""Tool 4 — Python Calculation Tool.

A single traced entry point over the deterministic domain services (GPA
normalization, eligibility checks, financial-need scoring, achievement
scoring, evaluation aggregation). Agents call these functions instead of
asking the LLM to do arithmetic — see build spec §24 and
``domain.services``.
"""

from __future__ import annotations

from typing import Any

from scholarai.domain.models.documents import Achievement, ExtractedApplicationData
from scholarai.domain.models.evaluation import ComponentScores
from scholarai.domain.models.scholarship import ScholarshipPreset
from scholarai.domain.services.academic_scoring import AcademicScore, score_academic_performance
from scholarai.domain.services.achievement_scoring import AchievementScore, score_achievements
from scholarai.domain.services.eligibility_rules import EligibilityCheck, check_eligibility
from scholarai.domain.services.evaluation import build_evaluation
from scholarai.domain.services.financial_need import FinancialNeedScore, score_financial_need
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


def _log(kind: str, application_id: str, **fields: Any) -> None:
    log.info("tool.calculation", kind=kind, application_id=application_id, **fields)


def calculate_eligibility(
    data: ExtractedApplicationData, preset: ScholarshipPreset, *, application_id: str
) -> EligibilityCheck:
    result = check_eligibility(data, preset.requirements)
    _log("eligibility", application_id, eligible=result.eligible, failed=len(result.failed_requirements))
    return result


def calculate_academic_score(data: ExtractedApplicationData, *, application_id: str) -> AcademicScore:
    result = score_academic_performance(data.cgpa, data.semester_gpas, len(data.failed_courses))
    _log("academic", application_id, score=result.normalized_score, trend=result.trend)
    return result


def calculate_financial_need(data: ExtractedApplicationData, *, application_id: str) -> FinancialNeedScore:
    result = score_financial_need(data)
    _log("financial_need", application_id, score=result.score, missing=len(result.missing_fields))
    return result


def calculate_achievement_score(achievements: tuple[Achievement, ...], *, application_id: str) -> AchievementScore:
    result = score_achievements(achievements)
    _log("achievements", application_id, score=result.score, count=result.evaluated)
    return result


def calculate_final_evaluation(
    application_id: str,
    scores: ComponentScores,
    preset: ScholarshipPreset,
    eligible: bool,
    extra_review_reasons: tuple[str, ...] = (),
):
    result = build_evaluation(application_id, scores, preset.weights, preset.thresholds, eligible, extra_review_reasons)
    _log(
        "final_evaluation",
        application_id,
        overall_score=result.overall_score,
        recommendation=result.recommendation.value,
        requires_human_review=result.requires_human_review,
    )
    return result
