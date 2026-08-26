"""Document Analysis Agent (build spec §5).

Combines the deterministic regex-based extraction pass
(``infrastructure.documents.extraction``) with an optional LLM refinement
step. The deterministic draft always wins for any field it found — the LLM
is only asked to fill gaps the regex pass left ``None``, using facts
explicitly present in the text, never to invent a number.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.documents import Document, ExtractedApplicationData
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AgentResult, AgentStatus
from scholarai.infrastructure.documents.extraction import build_extracted_data
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "document_agent"
log = get_logger(__name__)

_SYSTEM = (
    "You are the Document Analysis Agent for a university scholarship evaluation system. "
    "You are given raw text extracted from an applicant's documents and a draft of already-"
    "extracted fields. Fill in ONLY the fields that are null in the draft, and ONLY if the "
    "value is explicitly stated in the text. Never estimate, guess, or invent a number. If a "
    "field cannot be found, leave it null."
)


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    application_id = state["application_id"]
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))

    document_count = len(state.get("documents", []))
    add_trace(trace, AGENT_NAME, "processing", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, f"extract structured data from {document_count} document(s)")

    documents = [Document.model_validate(doc) for doc in state.get("documents", [])]
    async with timed() as t:
        draft = build_extracted_data(documents)
        extracted = await _refine_with_llm(deps, draft, documents, application_id)

    evidence, findings, issues = _summarize(extracted, documents)
    confidence = _confidence(extracted)
    has_no_unreadable = not extracted.unreadable_documents
    status = AgentStatus.SUCCESS if extracted.cgpa is not None and has_no_unreadable else AgentStatus.WARNING

    result = AgentResult(
        agent_name=AGENT_NAME,
        status=status,
        findings=tuple(findings),
        evidence=tuple(evidence),
        confidence=confidence,
        issues=tuple(issues),
    )

    add_trace(
        trace,
        AGENT_NAME,
        "processing",
        TraceStatus.COMPLETED,
        detail=f"{len(documents)} document(s) processed",
        duration_ms=t["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", f"extracted {len(findings)} fact(s), {len(issues)} issue(s)")

    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")

    return {
        "extracted_data": extracted.model_dump(mode="json"),
        "agent_results": agent_results,
        "trace": trace,
        "messages": messages,
    }


async def _refine_with_llm(
    deps: AgentDeps, draft: ExtractedApplicationData, documents: list[Document], application_id: str
) -> ExtractedApplicationData:
    if deps.llm.provider_name == "offline":
        return draft

    raw_text = "\n\n---\n\n".join(f"[{doc.filename}]\n{doc.raw_text[:4000]}" for doc in documents if doc.readable)
    user = (
        f"DRAFT (already extracted, do not overwrite non-null fields):\n{draft.model_dump_json()}\n\n"
        f"RAW DOCUMENT TEXT:\n{raw_text}"
    )
    try:
        refined = await deps.llm.complete_structured(_SYSTEM, user, ExtractedApplicationData)
    except AgentExecutionError as exc:
        log.warning("agent.document_analysis.llm_refine_failed", application_id=application_id, error=str(exc))
        return draft

    merged = draft.model_dump()
    for field, value in refined.model_dump().items():
        current = merged.get(field)
        is_empty = current in (None, (), [])
        if is_empty and value not in (None, (), []):
            merged[field] = value
    return ExtractedApplicationData.model_validate(merged)


def _summarize(
    data: ExtractedApplicationData, documents: list[Document]
) -> tuple[list[Evidence], list[str], list[str]]:
    evidence: list[Evidence] = []
    findings: list[str] = []
    issues: list[str] = []

    transcript = next(
        (d for d in documents if d.readable and d.raw_text and d.document_type.value == "transcript"), None
    )
    if data.cgpa is not None:
        findings.append(f"CGPA {data.cgpa:.2f} extracted from submitted documents")
        evidence.append(
            Evidence(
                source=transcript.filename if transcript else "Academic Transcript",
                detail=f"CGPA reported as {data.cgpa:.2f}",
                quality=EvidenceQuality.DIRECT,
            )
        )
    else:
        issues.append("CGPA could not be found in any submitted document")

    if data.documents_missing:
        issues.append(f"missing document(s): {', '.join(data.documents_missing)}")
    if data.unreadable_documents:
        issues.append(f"unreadable document(s): {', '.join(data.unreadable_documents)}")
    if data.achievements:
        findings.append(f"{len(data.achievements)} achievement(s) identified")

    return evidence, findings, issues


def _confidence(data: ExtractedApplicationData) -> float:
    key_fields = (data.student_id, data.cgpa, data.credits_completed, data.current_semester)
    found = sum(1 for field in key_fields if field is not None)
    return round(found / len(key_fields), 2)
