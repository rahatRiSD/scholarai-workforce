"""Verification Agent (build spec §11).

Cross-checks values as reported by *different* documents (e.g. a CGPA typed
into an application form vs. the CGPA the transcript actually states).
Re-runs the deterministic regex extractor per-document (rather than trusting
only the already-merged ``extracted_data``) so a discrepancy between two
sources isn't silently lost in the merge.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.models.documents import Document
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AgentStatus, VerificationResult
from scholarai.domain.services.verification import find_cgpa_conflict
from scholarai.infrastructure.documents.extraction import extract_from_text
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "verification_agent"
log = get_logger(__name__)


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "cross-checking submitted information", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "cross-check data across all submitted documents")

    documents = [Document.model_validate(d) for d in state.get("documents", [])]

    async with timed() as t:
        cgpa_by_source: dict[str, float] = {}
        for document in documents:
            if not document.readable:
                continue
            fields = extract_from_text(document.filename, document.raw_text)
            if "cgpa" in fields:
                cgpa_by_source[document.filename] = fields["cgpa"]

        conflicts: list[str] = []
        evidence: list[Evidence] = []
        values = list(cgpa_by_source.items())
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                (source_a, value_a), (source_b, value_b) = values[i], values[j]
                conflict = find_cgpa_conflict(value_a, value_b)
                if conflict:
                    conflicts.append(conflict.describe())
                    evidence.append(
                        Evidence(
                            source=f"{source_a} vs {source_b}",
                            detail=conflict.describe(),
                            quality=EvidenceQuality.DIRECT,
                        )
                    )

        unsupported = _find_unsupported_achievement_claims(state)
        missing_evidence = list(state.get("extracted_data", {}).get("documents_missing", []))

    conflict_detected = bool(conflicts)
    status = AgentStatus.WARNING if conflict_detected else AgentStatus.SUCCESS

    result = VerificationResult(
        agent_name=AGENT_NAME,
        status=status,
        findings=(f"{len(cgpa_by_source)} source(s) compared; {len(conflicts)} conflict(s) found",),
        evidence=tuple(evidence),
        confidence=0.9,
        issues=tuple(conflicts),
        conflicts=tuple(conflicts),
        unsupported_claims=tuple(unsupported),
        missing_evidence=tuple(missing_evidence),
        conflict_detected=conflict_detected,
    )

    add_trace(
        trace,
        AGENT_NAME,
        "cross-checking submitted information",
        TraceStatus.COMPLETED,
        detail="CONFLICT DETECTED" if conflict_detected else "no conflicts",
        duration_ms=t["ms"],
    )
    add_message(
        messages,
        AGENT_NAME,
        "supervisor",
        "CONFLICT DETECTED" if conflict_detected else "no conflicts found across submitted documents",
    )

    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")
    conflicts_state = list(state.get("conflicts", [])) + conflicts
    return {
        "agent_results": agent_results,
        "conflicts": conflicts_state,
        "trace": trace,
        "messages": messages,
    }


def _find_unsupported_achievement_claims(state: dict[str, Any]) -> list[str]:
    achievements = state.get("extracted_data", {}).get("achievements", [])
    return [a["title"] for a in achievements if not a.get("evidence_document")]
