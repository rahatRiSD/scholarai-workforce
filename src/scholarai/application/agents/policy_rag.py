"""Policy / RAG Agent (build spec §10) — one of the most important agents.

Retrieves relevant chunks from the university policy knowledge base
*before* making any policy-related claim. If retrieval returns nothing
relevant, the agent must say so explicitly ("Evidence unavailable.") rather
than asserting a policy exists — this is enforced structurally here: every
question that fails to retrieve above ``_RELEVANCE_THRESHOLD`` gets an
``UNAVAILABLE`` evidence entry, never a fabricated one.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.application.tools.rag_tool import search_policy
from scholarai.application.tools.web_search_tool import search_web
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AgentStatus, PolicyResult
from scholarai.domain.scholarship_presets import get_preset
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "policy_agent"
log = get_logger(__name__)
_RELEVANCE_THRESHOLD = 0.15

_SYSTEM = (
    "You are the Policy Agent. You are given retrieved excerpts from the university's policy "
    "documents plus a question. Answer ONLY using the excerpts provided. If the excerpts do not "
    "answer the question, say so explicitly rather than guessing. Cite the source document for "
    "every claim you make."
)


def _questions_for(preset_name: str) -> list[str]:
    return [
        f"What is the minimum CGPA and credit requirement for the {preset_name}?",
        f"What documents are required for the {preset_name}?",
        f"Are there disciplinary or conduct conditions for the {preset_name}?",
        f"What priority or additional criteria apply to the {preset_name}?",
    ]


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "retrieving policy evidence", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "retrieve and interpret relevant scholarship policy")

    preset = get_preset(state["scholarship_code"])
    application_id = state["application_id"]

    async with timed() as t:
        evidence: list[Evidence] = []
        answered: list[str] = []
        all_citations = []
        for question in _questions_for(preset.name):
            chunks = await search_policy(deps.retriever, question, application_id=application_id)
            relevant = [c for c in chunks if c.score >= _RELEVANCE_THRESHOLD]
            if not relevant:
                evidence.append(
                    Evidence(
                        source="Policy Knowledge Base",
                        detail=f'No supporting policy text found for: "{question}". Evidence unavailable.',
                        quality=EvidenceQuality.UNAVAILABLE,
                    )
                )
                continue
            for chunk in relevant:
                all_citations.append(chunk)
                evidence.append(
                    Evidence(
                        source=chunk.source,
                        detail=question,
                        quality=EvidenceQuality.DIRECT,
                        quote=chunk.text[:400],
                        page_or_section=chunk.section,
                    )
                )
            answered.append(question)

        interpretation = await _interpret(deps, preset.name, all_citations)
        public_context = await _public_policy_context(deps, preset.name, application_id)
        evidence.extend(public_context)

    citations_found = len(all_citations)
    status = AgentStatus.SUCCESS if citations_found else AgentStatus.WARNING

    result = PolicyResult(
        agent_name=AGENT_NAME,
        status=status,
        findings=(interpretation,),
        evidence=tuple(evidence),
        confidence=min(1.0, 0.4 + 0.15 * citations_found),
        issues=() if citations_found else ("no supporting policy evidence retrieved for any question",),
        policy_questions_answered=tuple(answered),
        interpretation=interpretation,
        citations_found=citations_found,
    )

    add_trace(
        trace,
        AGENT_NAME,
        "retrieving policy evidence",
        TraceStatus.COMPLETED,
        detail=f"{citations_found} internal citation(s); {len(public_context)} public source(s)",
        duration_ms=t["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", f"retrieved {citations_found} policy citation(s)")

    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")
    policy_evidence = [e.model_dump(mode="json") for e in evidence]
    return {
        "agent_results": agent_results,
        "policy_evidence": policy_evidence,
        "trace": trace,
        "messages": messages,
    }


async def _public_policy_context(deps: AgentDeps, scholarship_name: str, application_id: str) -> list[Evidence]:
    """Retrieve non-personal public context; never send applicant data externally."""
    if deps.web_search is None:
        return []
    query = f'official university scholarship eligibility guidance "{scholarship_name}"'
    try:
        results = await search_web(deps.web_search, query, application_id=application_id, max_results=3)
    except Exception as exc:  # noqa: BLE001 - public search is supplementary and must degrade safely
        log.warning("agent.policy.web_search_failed", error=str(exc))
        return []
    return [
        Evidence(
            source=item.url or item.title or "Public web search",
            detail="Supplementary public scholarship-policy context; not used as authoritative scoring policy",
            quote=item.snippet[:400],
            quality=EvidenceQuality.INFERRED,
        )
        for item in results[:3]
    ]


async def _interpret(deps: AgentDeps, scholarship_name: str, citations: list[Any]) -> str:
    if not citations:
        return "Evidence unavailable: no relevant policy text was retrieved from the knowledge base."
    if deps.llm.provider_name == "offline":
        joined = " | ".join(f"{c.source}: {c.text[:120]}" for c in citations[:3])
        return f"[offline mode] Retrieved policy excerpts for {scholarship_name}: {joined}"

    excerpts = "\n\n".join(f"[{c.source} — {c.section or 'n/a'}]\n{c.text}" for c in citations)
    try:
        return await deps.llm.complete(_SYSTEM, f"SCHOLARSHIP: {scholarship_name}\n\nEXCERPTS:\n{excerpts}")
    except AgentExecutionError as exc:
        log.warning("agent.policy.interpretation_failed", error=str(exc))
        return "Evidence retrieved but interpretation failed; see raw citations."
