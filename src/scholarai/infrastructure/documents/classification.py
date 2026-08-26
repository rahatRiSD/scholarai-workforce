"""Deterministic, keyword-based document-type classification.

Runs before any LLM call — "identify document types" (build spec §5) doesn't
need semantic understanding, just a look at the filename and the first page
of content, so it stays fast, free, and reproducible.
"""

from __future__ import annotations

from scholarai.domain.models.documents import DocumentType

_KEYWORDS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.TRANSCRIPT: ("transcript", "cgpa", "gpa", "semester", "credits earned", "grade report"),
    DocumentType.FINANCIAL_STATEMENT: (
        "income",
        "financial aid",
        "tuition",
        "household",
        "financial statement",
        "bank statement",
    ),
    DocumentType.RECOMMENDATION_LETTER: ("recommend", "reference letter", "letter of support"),
    DocumentType.CERTIFICATE: ("certificate", "certify", "award", "competition", "achievement"),
    DocumentType.IDENTIFICATION: ("passport", "national id", "identity card", "date of birth"),
    DocumentType.PERSONAL_STATEMENT: ("personal statement", "statement of purpose", "essay"),
}


def classify_document(filename: str, text: str) -> DocumentType:
    haystack = f"{filename.lower()} {text[:2000].lower()}"
    for document_type, keywords in _KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return document_type
    return DocumentType.OTHER
