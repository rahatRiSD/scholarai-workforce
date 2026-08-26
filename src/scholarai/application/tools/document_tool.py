"""Tool 1 — Document Reader.

Reads uploaded scholarship/student documents (PDF, TXT, DOCX) and returns
extracted, typed ``Document`` objects. Used by the Document Analysis Agent.
"""

from __future__ import annotations

from scholarai.domain.models.documents import Document, DocumentType
from scholarai.domain.ports.documents import DocumentReader
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


def read_documents(reader: DocumentReader, files: list[tuple[str, bytes]], *, application_id: str) -> list[Document]:
    """Read every uploaded file, tolerating individual failures.

    A single unreadable file must not abort the whole application — it's
    reported as an ``unreadable`` document instead (build spec §5: "detect
    unreadable documents").
    """
    documents: list[Document] = []
    for filename, content in files:
        try:
            document = reader.read(filename, content)
            log.info(
                "tool.document_reader",
                application_id=application_id,
                filename=filename,
                document_type=document.document_type.value,
                pages=document.page_count,
                readable=document.readable,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately tolerant, see docstring
            log.warning("tool.document_reader.failed", application_id=application_id, filename=filename, error=str(exc))
            document = Document(
                filename=filename,
                document_type=DocumentType.UNREADABLE,
                raw_text="",
                readable=False,
            )
        documents.append(document)
    return documents
