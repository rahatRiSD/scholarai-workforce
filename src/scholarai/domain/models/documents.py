"""Documents an applicant submits, and the structured facts extracted from them."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    TRANSCRIPT = "transcript"
    FINANCIAL_STATEMENT = "financial_statement"
    RECOMMENDATION_LETTER = "recommendation_letter"
    CERTIFICATE = "certificate"
    IDENTIFICATION = "identification"
    PERSONAL_STATEMENT = "personal_statement"
    OTHER = "other"
    UNREADABLE = "unreadable"


class Document(BaseModel):
    """A single uploaded file, after text extraction.

    ``raw_text`` is kept off the frozen-envelope's ``repr`` in logs (see
    ``infrastructure.observability.logging``) because it can contain personal
    data; it's still a normal field so agents can read it.
    """

    model_config = ConfigDict(frozen=True)

    filename: str
    document_type: DocumentType
    raw_text: str = ""
    page_count: int = 0
    readable: bool = True


class Achievement(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str = Field(description="e.g. competition, publication, leadership, volunteering")
    title: str
    description: str = ""
    year: int | None = None
    evidence_document: str | None = None


class ExtractedApplicationData(BaseModel):
    """Structured facts the Document Analysis Agent pulls out of the uploads.

    This is the shared substrate every downstream specialist reads from — it
    is never invented by an LLM past what a document actually states.
    Anything not found stays ``None`` and is listed in ``documents_missing``.
    """

    model_config = ConfigDict(frozen=True)

    student_name: str | None = None
    student_id: str | None = None
    program: str | None = None
    department: str | None = None
    cgpa: float | None = None
    credits_completed: int | None = None
    current_semester: int | None = None
    graduation_year: int | None = None
    semester_gpas: tuple[float, ...] = Field(
        default=(), description="Chronological per-semester GPA, oldest first, if the transcript reports it"
    )
    failed_courses: tuple[str, ...] = ()
    achievements: tuple[Achievement, ...] = ()
    family_income_annual: float | None = None
    household_size: int | None = None
    dependents: int | None = None
    tuition_cost_annual: float | None = None
    financial_aid_already_received: float | None = None
    documents_present: tuple[DocumentType, ...] = ()
    documents_missing: tuple[str, ...] = ()
    unreadable_documents: tuple[str, ...] = ()
