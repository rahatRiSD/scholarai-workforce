"""Dispatches to the right reader by file extension; implements ``DocumentReader``."""

from __future__ import annotations

from scholarai.domain.errors import DocumentProcessingError
from scholarai.domain.models.documents import Document
from scholarai.infrastructure.documents.docx_reader import DocxDocumentReader
from scholarai.infrastructure.documents.pdf_reader import PdfDocumentReader
from scholarai.infrastructure.documents.txt_reader import TxtDocumentReader


class CompositeDocumentReader:
    def __init__(self) -> None:
        self._readers = (PdfDocumentReader(), TxtDocumentReader(), DocxDocumentReader())

    def supports(self, filename: str) -> bool:
        return any(reader.supports(filename) for reader in self._readers)

    def read(self, filename: str, content: bytes) -> Document:
        for reader in self._readers:
            if reader.supports(filename):
                return reader.read(filename, content)
        msg = f"unsupported document type for {filename!r}"
        raise DocumentProcessingError(msg)
