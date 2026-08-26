from scholarai.domain.services.verification import find_cgpa_conflict


def test_matching_cgpa_reports_no_conflict():
    assert find_cgpa_conflict(3.80, 3.80) is None


def test_within_tolerance_reports_no_conflict():
    assert find_cgpa_conflict(3.801, 3.799) is None


def test_mismatched_cgpa_reports_conflict():
    conflict = find_cgpa_conflict(3.95, 3.60)
    assert conflict is not None
    assert "CONFLICT DETECTED" in conflict.describe()
    assert "3.95" in conflict.describe()
    assert "3.60" in conflict.describe()


def test_missing_value_reports_no_conflict():
    assert find_cgpa_conflict(None, 3.5) is None
    assert find_cgpa_conflict(3.5, None) is None
