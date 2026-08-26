"""Deterministic financial-need scoring.

Never invents a number: any missing input is reported in ``missing_fields``
and the caller (the Financial Need Agent) is responsible for surfacing
``UNKNOWN / NEEDS HUMAN REVIEW`` rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

from scholarai.domain.models.documents import ExtractedApplicationData

_REQUIRED_FIELDS = ("family_income_annual", "household_size", "tuition_cost_annual")


@dataclass(frozen=True)
class FinancialNeedScore:
    score: float | None
    missing_fields: tuple[str, ...]
    needs_human_review: bool
    affordability_ratio: float | None = None


def score_financial_need(data: ExtractedApplicationData) -> FinancialNeedScore:
    missing = [field for field in _REQUIRED_FIELDS if getattr(data, field) is None]
    if missing:
        return FinancialNeedScore(score=None, missing_fields=tuple(missing), needs_human_review=True)

    income = max(data.family_income_annual or 0.0, 1.0)
    household_size = max(data.household_size or 1, 1)
    tuition = max(data.tuition_cost_annual or 0.0, 0.0)
    dependents = data.dependents or 0
    aid_received = data.financial_aid_already_received or 0.0

    income_per_capita = income / household_size
    # Tuition burden relative to income: 0 = trivial, 1+ = tuition consumes the
    # household's entire annual income or more.
    affordability_ratio = round(tuition / income, 3)

    burden_score = min(affordability_ratio, 1.5) / 1.5 * 70.0
    dependents_score = min(dependents, 5) / 5.0 * 15.0
    low_income_score = max(0.0, (30_000.0 - min(income_per_capita, 30_000.0)) / 30_000.0) * 15.0

    raw_score = burden_score + dependents_score + low_income_score
    aid_offset = min(raw_score, (aid_received / income) * 100.0) if income else 0.0
    score = round(max(0.0, min(100.0, raw_score - aid_offset)), 2)

    return FinancialNeedScore(
        score=score,
        missing_fields=(),
        needs_human_review=False,
        affordability_ratio=affordability_ratio,
    )
