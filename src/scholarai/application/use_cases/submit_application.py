"""Create a new application and attach its uploaded documents."""

from __future__ import annotations

from scholarai.application.orchestration.state import new_state
from scholarai.application.tools.document_tool import read_documents
from scholarai.application.use_cases.application_store import ApplicationStore
from scholarai.domain.errors import ScholarAIError
from scholarai.domain.models.application import Application, ApplicationStatus, new_application_id
from scholarai.domain.ports.documents import DocumentReader
from scholarai.domain.scholarship_presets import get_preset
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


def create_application(
    store: ApplicationStore,
    document_reader: DocumentReader,
    scholarship_code: str,
    files: list[tuple[str, bytes]],
) -> Application:
    try:
        get_preset(scholarship_code)
    except ValueError as exc:
        raise ScholarAIError(str(exc)) from exc

    application_id = new_application_id()
    documents = read_documents(document_reader, files, application_id=application_id)

    state = new_state(application_id, scholarship_code)
    state["documents"] = [document.model_dump(mode="json") for document in documents]
    store.save(application_id, state)

    log.info(
        "use_case.submit_application",
        application_id=application_id,
        scholarship_code=scholarship_code,
        documents=len(documents),
    )
    return Application(
        application_id=application_id, scholarship_code=scholarship_code, status=ApplicationStatus.RECEIVED
    )
