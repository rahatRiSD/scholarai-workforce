"""Deterministic cross-checking between extracted application data sources.

The Verification Agent uses this to catch contradictions before the
Evaluation Agent ever sees the data — e.g. a CGPA the applicant *typed* in
the application form disagreeing with the CGPA the transcript actually
states. Anything numeric is compared here in Python; the LLM layer only
narrates what was found.
"""

from __future__ import annotations

from dataclasses import dataclass

_CGPA_TOLERANCE = 0.01


@dataclass(frozen=True)
class FieldConflict:
    field: str
    application_value: str
    transcript_value: str

    def describe(self) -> str:
        return (
            f"CONFLICT DETECTED: {self.field} — application says "
            f"'{self.application_value}', transcript says '{self.transcript_value}'"
        )


def find_cgpa_conflict(application_cgpa: float | None, transcript_cgpa: float | None) -> FieldConflict | None:
    if application_cgpa is None or transcript_cgpa is None:
        return None
    if abs(application_cgpa - transcript_cgpa) > _CGPA_TOLERANCE:
        return FieldConflict(
            field="cgpa",
            application_value=f"{application_cgpa:.2f}",
            transcript_value=f"{transcript_cgpa:.2f}",
        )
    return None
