"""Deterministic, regex-based first-pass extraction of structured facts.

Runs on every application regardless of LLM availability, so the pipeline
never depends on a paid API for its most basic numbers. When an LLM is
configured, the Document Analysis Agent uses this as a seed and asks the
model to refine/augment it — see
``application.agents.document_analysis``. Patterns are written against the
label conventions used by this project's own synthetic sample documents
(``data/sample_applications``); real-world deployments would extend or
replace these for whatever transcript/financial-form formats their
university actually issues.
"""

from __future__ import annotations

import re

from scholarai.domain.models.documents import (
    Achievement,
    Document,
    DocumentType,
    ExtractedApplicationData,
)

_PATTERNS = {
    "student_name": re.compile(r"(?:Student Name|Name)\s*:\s*(.+)", re.IGNORECASE),
    "student_id": re.compile(r"(?:Student ID|ID)\s*:\s*([A-Za-z0-9\-]+)", re.IGNORECASE),
    "program": re.compile(r"Program\s*:\s*(.+)", re.IGNORECASE),
    "department": re.compile(r"Department\s*:\s*(.+)", re.IGNORECASE),
    "cgpa": re.compile(r"(?:CGPA|GPA)\s*:\s*([0-4]\.\d{1,2})", re.IGNORECASE),
    "credits_completed": re.compile(r"Credits?\s*Completed\s*:\s*(\d+)", re.IGNORECASE),
    "current_semester": re.compile(r"(?:Current\s*)?Semester\s*:\s*(\d+)", re.IGNORECASE),
    "graduation_year": re.compile(r"(?:Expected\s*)?Graduation\s*Year\s*:\s*(\d{4})", re.IGNORECASE),
    "family_income_annual": re.compile(r"(?:Annual\s*)?Family\s*Income\s*:\s*\$?([\d,]+)", re.IGNORECASE),
    "household_size": re.compile(r"Household\s*Size\s*:\s*(\d+)", re.IGNORECASE),
    "dependents": re.compile(r"Dependents\s*:\s*(\d+)", re.IGNORECASE),
    "tuition_cost_annual": re.compile(r"(?:Annual\s*)?Tuition\s*:\s*\$?([\d,]+)", re.IGNORECASE),
    "financial_aid_already_received": re.compile(
        r"(?:Financial\s*Aid\s*Already\s*Received|Current\s*Aid)\s*:\s*\$?([\d,]+)", re.IGNORECASE
    ),
}
_SEMESTER_GPA_LINE = re.compile(r"Semester\s*\d+\s*GPA\s*:\s*([0-4]\.\d{1,2})", re.IGNORECASE)
_FAILED_COURSE_LINE = re.compile(r"(?:Failed|Grade:\s*F)\D*([A-Z]{2,4}\s?-?\d{3}[A-Za-z]?)", re.IGNORECASE)
_ACHIEVEMENT_LINE = re.compile(
    r"^\s*[-*]\s*\[(?P<category>[a-zA-Z ]+)\]\s*(?P<title>.+?)(?:\s*\((?P<year>\d{4})\))?\s*$"
)


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _parse_money(value: str | None) -> float | None:
    if value is None:
        return None
    return float(value.replace(",", ""))


def extract_from_text(document_filename: str, text: str) -> dict:
    """Return a dict of the fields this regex pass could confidently find."""
    found: dict = {}
    for field, pattern in _PATTERNS.items():
        value = _first_match(pattern, text)
        if value is None:
            continue
        if field in ("cgpa",):
            found[field] = float(value)
        elif field in ("credits_completed", "current_semester", "graduation_year", "household_size", "dependents"):
            found[field] = int(value)
        elif field in ("family_income_annual", "tuition_cost_annual", "financial_aid_already_received"):
            found[field] = _parse_money(value)
        else:
            found[field] = value

    semester_gpas = tuple(float(m) for m in _SEMESTER_GPA_LINE.findall(text))
    if semester_gpas:
        found["semester_gpas"] = semester_gpas

    failed_courses = tuple(dict.fromkeys(_FAILED_COURSE_LINE.findall(text)))
    if failed_courses:
        found["failed_courses"] = failed_courses

    achievements = []
    for line in text.splitlines():
        match = _ACHIEVEMENT_LINE.match(line)
        if match:
            achievements.append(
                Achievement(
                    category=match.group("category").strip().lower(),
                    title=match.group("title").strip(),
                    year=int(match.group("year")) if match.group("year") else None,
                    evidence_document=document_filename,
                )
            )
    if achievements:
        found["achievements"] = tuple(achievements)

    return found


_REQUIRED_APPLICATION_DOCUMENTS = ("transcript",)


def build_extracted_data(documents: list[Document]) -> ExtractedApplicationData:
    """Merge the regex pass across every document into one draft record."""
    merged: dict = {}
    achievements: list[Achievement] = []
    present: list[DocumentType] = []
    unreadable: list[str] = []

    for document in documents:
        if not document.readable or document.document_type is DocumentType.UNREADABLE:
            unreadable.append(document.filename)
            continue
        present.append(document.document_type)
        fields = extract_from_text(document.filename, document.raw_text)
        achievements.extend(fields.pop("achievements", ()))
        for key, value in fields.items():
            merged.setdefault(key, value)

    present_names = {doc.value for doc in present}
    missing = [name for name in _REQUIRED_APPLICATION_DOCUMENTS if name not in present_names]

    return ExtractedApplicationData(
        **merged,
        achievements=tuple(achievements),
        documents_present=tuple(present),
        documents_missing=tuple(missing),
        unreadable_documents=tuple(unreadable),
    )
