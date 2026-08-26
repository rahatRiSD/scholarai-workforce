from scholarai.domain.services.financial_need import score_financial_need
from tests.unit.factories import make_extracted_data


def test_missing_financial_fields_returns_unknown_needing_review():
    data = make_extracted_data(family_income_annual=None, household_size=None, tuition_cost_annual=None)
    result = score_financial_need(data)
    assert result.score is None
    assert result.needs_human_review is True
    assert "family_income_annual" in result.missing_fields


def test_high_tuition_low_income_scores_higher_need():
    low_income = make_extracted_data(
        family_income_annual=15000, household_size=5, tuition_cost_annual=12000, dependents=3
    )
    high_income = make_extracted_data(
        family_income_annual=150000, household_size=3, tuition_cost_annual=12000, dependents=1
    )
    low_income_result = score_financial_need(low_income)
    high_income_result = score_financial_need(high_income)
    assert low_income_result.score > high_income_result.score


def test_existing_aid_reduces_need_score():
    without_aid = make_extracted_data(
        family_income_annual=30000, household_size=4, tuition_cost_annual=15000, financial_aid_already_received=0
    )
    with_aid = make_extracted_data(
        family_income_annual=30000,
        household_size=4,
        tuition_cost_annual=15000,
        financial_aid_already_received=20000,
    )
    assert score_financial_need(with_aid).score < score_financial_need(without_aid).score


def test_score_is_bounded_0_to_100():
    extreme = make_extracted_data(
        family_income_annual=1, household_size=10, tuition_cost_annual=1_000_000, dependents=10
    )
    result = score_financial_need(extreme)
    assert 0.0 <= result.score <= 100.0
