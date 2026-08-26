from scholarai.domain.services.academic_scoring import (
    assess_consistency,
    detect_trend,
    normalize_cgpa,
    score_academic_performance,
)


def test_normalize_cgpa_scales_to_100():
    assert normalize_cgpa(4.0) == 100.0
    assert normalize_cgpa(2.0) == 50.0
    assert normalize_cgpa(0.0) == 0.0


def test_normalize_cgpa_clamps_out_of_range_values():
    assert normalize_cgpa(5.0) == 100.0
    assert normalize_cgpa(-1.0) == 0.0


def test_detect_trend_improving():
    assert detect_trend((3.0, 3.1, 3.6, 3.7)) == "improving"


def test_detect_trend_declining():
    assert detect_trend((3.8, 3.7, 3.1, 3.0)) == "declining"


def test_detect_trend_stable_when_flat():
    assert detect_trend((3.5, 3.51, 3.49, 3.5)) == "stable"


def test_detect_trend_unknown_with_insufficient_data():
    assert detect_trend((3.5,)) == "unknown"
    assert detect_trend(()) == "unknown"


def test_assess_consistency_bands():
    assert assess_consistency((3.5, 3.6, 3.55)) == "excellent"
    assert assess_consistency((3.0, 3.9)) == "fair"
    assert assess_consistency((2.4, 4.0)) == "poor"


def test_score_academic_performance_applies_failed_course_penalty():
    clean = score_academic_performance(cgpa=3.8, semester_gpas=(), failed_course_count=0)
    penalized = score_academic_performance(cgpa=3.8, semester_gpas=(), failed_course_count=2)
    assert penalized.normalized_score < clean.normalized_score
    assert penalized.failed_course_penalty == 10.0


def test_score_academic_performance_missing_cgpa_returns_zero():
    result = score_academic_performance(cgpa=None)
    assert result.normalized_score == 0.0
    assert result.trend == "unknown"
