"""Small builders for test fixtures — avoids repeating long constructor calls."""

from __future__ import annotations

from scholarai.domain.models.documents import Achievement, DocumentType, ExtractedApplicationData


def make_extracted_data(**overrides) -> ExtractedApplicationData:
    defaults = {
        "student_name": "Test Student",
        "student_id": "STU-0001",
        "program": "BSc Computer Science",
        "cgpa": 3.8,
        "credits_completed": 60,
        "current_semester": 4,
        "semester_gpas": (3.6, 3.7, 3.85, 3.9),
        "failed_courses": (),
        "achievements": (),
        "documents_present": (DocumentType.TRANSCRIPT,),
        "documents_missing": (),
        "unreadable_documents": (),
    }
    defaults.update(overrides)
    return ExtractedApplicationData(**defaults)


def make_achievement(**overrides) -> Achievement:
    defaults = {"category": "award", "title": "Dean's List", "evidence_document": "transcript.pdf"}
    defaults.update(overrides)
    return Achievement(**defaults)
