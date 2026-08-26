"""Deterministic academic scoring: CGPA normalization, trend, consistency.

The Academic Evaluation Agent calls this module for every number it reports.
The LLM layer only narrates the result — see
``application.agents.academic_evaluation``.
"""

from __future__ import annotations

from dataclasses import dataclass

_MAX_CGPA_SCALE = 4.0
_TREND_EPSILON = 0.05
"""GPA deltas smaller than this are noise, not a real trend."""


@dataclass(frozen=True)
class AcademicScore:
    normalized_score: float
    trend: str
    consistency: str
    failed_course_penalty: float


def normalize_cgpa(cgpa: float, scale: float = _MAX_CGPA_SCALE) -> float:
    """Map a CGPA to a 0-100 scale. Clamped so a bad upstream value can't escape."""
    if scale <= 0:
        msg = "scale must be positive"
        raise ValueError(msg)
    return round(max(0.0, min(cgpa, scale)) / scale * 100.0, 2)


def detect_trend(semester_gpas: tuple[float, ...]) -> str:
    """Classify a chronological semester-GPA series as improving/declining/stable.

    Compares the mean of the second half against the first half rather than
    just the last two points, so one noisy semester doesn't flip the verdict.
    """
    if len(semester_gpas) < 2:
        return "unknown"
    midpoint = len(semester_gpas) // 2
    first_half = semester_gpas[:midpoint] or semester_gpas[:1]
    second_half = semester_gpas[midpoint:]
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    delta = second_avg - first_avg
    if delta > _TREND_EPSILON:
        return "improving"
    if delta < -_TREND_EPSILON:
        return "declining"
    return "stable"


def assess_consistency(semester_gpas: tuple[float, ...]) -> str:
    """Grade academic consistency by the spread (max-min) of semester GPAs."""
    if len(semester_gpas) < 2:
        return "unknown"
    spread = max(semester_gpas) - min(semester_gpas)
    if spread <= 0.25:
        return "excellent"
    if spread <= 0.5:
        return "good"
    if spread <= 1.0:
        return "fair"
    return "poor"


def score_academic_performance(
    cgpa: float | None,
    semester_gpas: tuple[float, ...] = (),
    failed_course_count: int = 0,
    failed_course_penalty_points: float = 5.0,
) -> AcademicScore:
    """The single entry point the Academic Evaluation Agent uses for its numbers."""
    if cgpa is None:
        return AcademicScore(normalized_score=0.0, trend="unknown", consistency="unknown", failed_course_penalty=0.0)
    base = normalize_cgpa(cgpa)
    penalty = min(base, failed_course_count * failed_course_penalty_points)
    normalized = round(max(0.0, base - penalty), 2)
    return AcademicScore(
        normalized_score=normalized,
        trend=detect_trend(semester_gpas),
        consistency=assess_consistency(semester_gpas),
        failed_course_penalty=penalty,
    )
