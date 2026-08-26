"""Statement-of-Purpose Agent.

Produces a scholarship-specific SOP from verified application facts and the
already-computed evaluation.  It never invents institutions, achievements,
research interests, or career claims.  The result is a draft for the student
to review, not an autonomous submission.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AgentResult, AgentStatus
from scholarai.domain.scholarship_presets import get_preset
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "sop_agent"
log = get_logger(__name__)

_SYSTEM = """You are the Statement-of-Purpose Agent in a scholarship-review workforce.
Write a polished 650-900 word scholarship SOP in first person. Use only verified facts in
the supplied context. Do not invent achievements, institutions, research experience,
financial circumstances, goals, or personal stories. If a detail is missing, write around
it naturally rather than inserting a placeholder. Structure the draft with a compelling
opening, academic preparation, relevant achievements or service, motivation and goals,
scholarship fit, and a concise closing. Return only the SOP prose with paragraph breaks."""


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "drafting scholarship statement of purpose", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "draft an evidence-grounded statement of purpose")

    extracted = state.get("extracted_data") or {}
    evaluation = state.get("evaluation") or {}
    preset = get_preset(state["scholarship_code"])
    context = {
        "student_name": extracted.get("student_name"),
        "program": extracted.get("program"),
        "department": extracted.get("department"),
        "cgpa": extracted.get("cgpa"),
        "semester_gpas": extracted.get("semester_gpas", []),
        "achievements": extracted.get("achievements", []),
        "scholarship": preset.name,
        "scholarship_description": preset.description,
        "overall_score": evaluation.get("overall_score"),
        "component_scores": evaluation.get("component_scores", {}),
        "review_reasons": evaluation.get("review_reasons", []),
    }

    async with timed() as timer:
        if deps.llm.provider_name == "offline":
            sop = _offline_draft(context)
        else:
            try:
                sop = await deps.llm.complete(_SYSTEM, f"VERIFIED CONTEXT:\n{context}", temperature=0.35)
            except AgentExecutionError as exc:
                log.warning("agent.sop.generation_failed", error=str(exc))
                sop = _offline_draft(context)

    evidence = [
        Evidence(
            source="Verified application record",
            detail="SOP generated only from extracted facts and deterministic evaluation results",
            quality=EvidenceQuality.DIRECT,
        )
    ]
    result = AgentResult(
        agent_name=AGENT_NAME,
        status=AgentStatus.SUCCESS if sop.strip() else AgentStatus.WARNING,
        findings=(f"Generated a {len(sop.split())}-word SOP draft for student review",),
        evidence=tuple(evidence),
        confidence=0.9 if extracted.get("cgpa") is not None else 0.7,
        issues=() if sop.strip() else ("SOP generation returned empty text",),
    )

    add_trace(
        trace,
        AGENT_NAME,
        "drafting scholarship statement of purpose",
        TraceStatus.COMPLETED,
        detail=f"{len(sop.split())} words",
        duration_ms=timer["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", "SOP draft completed and ready for student review")
    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")
    return {"sop": sop, "agent_results": agent_results, "trace": trace, "messages": messages}


def _offline_draft(context: dict[str, Any]) -> str:
    name = context.get("student_name") or "I"
    program = context.get("program") or "my chosen academic program"
    cgpa = context.get("cgpa")
    scholarship = context.get("scholarship") or "this scholarship"
    achievements = context.get("achievements") or []
    academic_sentence = (
        f"My current CGPA of {cgpa:.2f} reflects consistent effort and a serious approach to learning."
        if isinstance(cgpa, (int, float))
        else "My academic record reflects sustained effort and a serious approach to learning."
    )
    achievement_sentence = ""
    if achievements:
        titles = ", ".join(str(item.get("title", "")).strip() for item in achievements[:3] if item.get("title"))
        if titles:
            achievement_sentence = (
                f" My documented activities include {titles}, experiences that strengthened my discipline and teamwork."
            )
    return (
        f"I am applying for the {scholarship} because it would allow me to continue developing through {program} "
        "with greater focus and responsibility. I view scholarship support not simply as financial assistance, "
        "but as a commitment "
        "to use educational opportunity thoughtfully and to contribute through reliable, ethical work.\n\n"
        f"{academic_sentence} My studies have taught me to approach difficult problems patiently, "
        "connect theory with practical decisions, and improve through feedback. I intend to build "
        "on this preparation by deepening my subject knowledge and participating actively "
        f"in the academic community.{achievement_sentence}\n\n"
        "The scholarship aligns with my goal of sustaining strong academic progress while developing "
        "the judgment and communication skills needed for meaningful professional work. If selected, "
        "I will treat the award as both recognition and accountability: I will maintain "
        "high standards, seek opportunities to support peers, and document my progress honestly.\n\n"
        f"Thank you for considering my application. {name if name != 'I' else 'I'} would be "
        "honored to receive this support and to demonstrate, "
        "through continued effort and responsible participation, the value of the opportunity provided."
    )
