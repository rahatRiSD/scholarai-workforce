"""Deterministic eligibility checks against a scholarship's numeric requirements.

Ambiguous, non-numeric policy language is deliberately out of scope here —
that's the Policy/RAG Agent's job. This module only ever compares numbers and
set membership, so its verdict is reproducible and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scholarai.domain.models.documents import ExtractedApplicationData
from scholarai.domain.models.scholarship import EligibilityRequirements


@dataclass(frozen=True)
class EligibilityCheck:
    eligible: bool
    requirements_checked: tuple[str, ...]
    failed_requirements: tuple[str, ...]
    missing_data_requirements: tuple[str, ...] = field(default_factory=tuple)


def check_eligibility(
    data: ExtractedApplicationData,
    requirements: EligibilityRequirements,
) -> EligibilityCheck:
    checked: list[str] = []
    failed: list[str] = []
    missing: list[str] = []

    if data.cgpa is None:
        missing.append(f"CGPA unknown; cannot verify minimum CGPA of {requirements.min_cgpa}")
    else:
        checked.append(f"CGPA {data.cgpa:.2f} >= minimum {requirements.min_cgpa:.2f}")
        if data.cgpa < requirements.min_cgpa:
            failed.append(f"CGPA {data.cgpa:.2f} is below the minimum required {requirements.min_cgpa:.2f}")

    if data.credits_completed is None:
        missing.append(f"credits completed unknown; cannot verify minimum of {requirements.min_credits_completed}")
    else:
        checked.append(f"credits completed {data.credits_completed} >= minimum {requirements.min_credits_completed}")
        if data.credits_completed < requirements.min_credits_completed:
            failed.append(
                f"only {data.credits_completed} credits completed; minimum is {requirements.min_credits_completed}"
            )

    if data.current_semester is None:
        missing.append(f"current semester unknown; cannot verify minimum semester {requirements.min_semester}")
    else:
        checked.append(f"semester {data.current_semester} >= minimum {requirements.min_semester}")
        if data.current_semester < requirements.min_semester:
            failed.append(
                f"student is in semester {data.current_semester}; minimum required is {requirements.min_semester}"
            )

    checked.append(f"failed courses ({len(data.failed_courses)}) <= maximum {requirements.max_failed_courses}")
    if len(data.failed_courses) > requirements.max_failed_courses:
        failed.append(
            f"{len(data.failed_courses)} failed course(s) exceeds the maximum of {requirements.max_failed_courses}"
        )

    present_names = {doc.value for doc in data.documents_present}
    for required_document in requirements.required_documents:
        checked.append(f"required document present: {required_document}")
        if required_document not in present_names:
            failed.append(f"required document missing: {required_document}")

    eligible = not failed and not missing
    return EligibilityCheck(
        eligible=eligible,
        requirements_checked=tuple(checked),
        failed_requirements=tuple(failed),
        missing_data_requirements=tuple(missing),
    )
