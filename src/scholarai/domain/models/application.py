"""Core application entities: the student and their scholarship application."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatus(StrEnum):
    """Where an application sits in the workflow — mirrors the LangGraph state."""

    RECEIVED = "received"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


class Student(BaseModel):
    """Identity fields extracted from an application's documents.

    Only ``student_id`` should ever be used in logs or cross-request
    identifiers — see ``docs/PRIVACY.md`` for why the name is kept out of
    structured logs.
    """

    model_config = ConfigDict(frozen=True)

    student_id: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    program: str | None = None
    department: str | None = None


def new_application_id() -> str:
    return f"APP-{uuid4().hex[:8].upper()}"


class Application(BaseModel):
    """A scholarship application: the unit of work the whole workflow tracks."""

    model_config = ConfigDict(frozen=True)

    application_id: str = Field(default_factory=new_application_id)
    scholarship_code: str
    student: Student | None = None
    status: ApplicationStatus = ApplicationStatus.RECEIVED
    created_at: datetime = Field(default_factory=datetime.utcnow)
