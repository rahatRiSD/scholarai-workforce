"""PDF text extraction via PyMuPDF."""

from __future__ import annotations

import fitz  # PyMuPDF

from scholarai.domain.models.documents import Document, DocumentType
from scholarai.infrastructure.documents.classification import classify_document
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


class PdfDocumentReader:
    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def read(self, filename: str, content: bytes) -> Document:
        try:
            with fitz.open(stream=content, filetype="pdf") as pdf:
                pages = [page.get_text() for page in pdf]
                text = "\n".join(pages).strip()
                page_count = pdf.page_count
        except Exception as exc:  # noqa: BLE001 - any malformed PDF must degrade, not crash
            log.warning("documents.pdf_reader.failed", filename=filename, error=str(exc))
            return Document(filename=filename, document_type=DocumentType.UNREADABLE, readable=False)

        if not text:
            return Document(
                filename=filename,
                document_type=DocumentType.UNREADABLE,
                page_count=page_count,
                readable=False,
            )
        return Document(
            filename=filename,
            document_type=classify_document(filename, text),
            raw_text=text,
            page_count=page_count,
            readable=True,
        )
