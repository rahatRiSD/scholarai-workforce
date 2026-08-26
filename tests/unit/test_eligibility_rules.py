from scholarai.domain.models.scholarship import EligibilityRequirements
from scholarai.domain.services.eligibility_rules import check_eligibility
from tests.unit.factories import make_extracted_data

REQUIREMENTS = EligibilityRequirements(
    min_cgpa=3.5,
    min_credits_completed=30,
    min_semester=2,
    max_failed_courses=0,
    required_documents=("transcript",),
)


def test_eligible_student_passes_all_checks():
    data = make_extracted_data(cgpa=3.9, credits_completed=60, current_semester=4)
    result = check_eligibility(data, REQUIREMENTS)
    assert result.eligible is True
    assert not result.failed_requirements
    assert not result.missing_data_requirements


def test_low_cgpa_fails_eligibility():
    data = make_extracted_data(cgpa=3.0)
    result = check_eligibility(data, REQUIREMENTS)
    assert result.eligible is False
    assert any("CGPA" in reason for reason in result.failed_requirements)


def test_missing_cgpa_is_reported_as_missing_not_failed():
    data = make_extracted_data(cgpa=None)
    result = check_eligibility(data, REQUIREMENTS)
    assert result.eligible is False
    assert result.missing_data_requirements
    assert not any("CGPA" in reason for reason in result.failed_requirements)


def test_missing_required_document_fails_eligibility():
    data = make_extracted_data(documents_present=())
    result = check_eligibility(data, REQUIREMENTS)
    assert result.eligible is False
    assert any("transcript" in reason for reason in result.failed_requirements)


def test_too_many_failed_courses_fails_eligibility():
    data = make_extracted_data(failed_courses=("CS201",))
    result = check_eligibility(data, REQUIREMENTS)
    assert result.eligible is False
