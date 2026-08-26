"""Port for extracting text from uploaded documents."""

from __future__ import annotations

from typing import Protocol

from scholarai.domain.models.documents import Document


class DocumentReader(Protocol):
    """Reads a document's raw bytes and returns extracted text + page count."""

    def supports(self, filename: str) -> bool: ...

    def read(self, filename: str, content: bytes) -> Document: ...
