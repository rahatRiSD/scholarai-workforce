"""Plain-text document reading."""

from __future__ import annotations

from scholarai.domain.models.documents import Document, DocumentType
from scholarai.infrastructure.documents.classification import classify_document


class TxtDocumentReader:
    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".txt")

    def read(self, filename: str, content: bytes) -> Document:
        text = content.decode("utf-8", errors="ignore").strip()
        if not text:
            return Document(filename=filename, document_type=DocumentType.UNREADABLE, readable=False)
        return Document(
            filename=filename,
            document_type=classify_document(filename, text),
            raw_text=text,
            page_count=1,
            readable=True,
        )
