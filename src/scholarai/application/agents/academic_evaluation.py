"""Academic Evaluation Agent (build spec §7).

All numbers come from ``domain.services.academic_scoring`` — the LLM never
performs arithmetic; it only classifies the overall academic picture in
words (e.g. "Excellent") over numbers it is handed, and that classification
is still cross-checked against the deterministic normalized score band.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.documents import ExtractedApplicationData
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AcademicResult, AgentStatus
from scholarai.domain.services.academic_scoring import score_academic_performance
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "academic_agent"
log = get_logger(__name__)

_SYSTEM = (
    "You are the Academic Evaluation Agent. You are given deterministically computed academic "
    "numbers (never recompute them). Write a one or two sentence qualitative assessment "
    "consistent with the numbers - e.g. a normalized score above 85 with an improving trend "
    "should read as strong, not lukewarm."
)

_BAND_LABELS = (
    (85.0, "Excellent"),
    (70.0, "Strong"),
    (55.0, "Satisfactory"),
    (0.0, "Needs Improvement"),
)


def _band_label(score: float) -> str:
    for threshold, label in _BAND_LABELS:
        if score >= threshold:
            return label
    return "Needs Improvement"


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "scoring academic performance", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "compute academic performance score")

    data = ExtractedApplicationData.model_validate(state["extracted_data"])

    async with timed() as t:
        score = score_academic_performance(data.cgpa, data.semester_gpas, len(data.failed_courses))
        label = _band_label(score.normalized_score)
        assessment = f"{label}: normalized score {score.normalized_score:.1f}/100, trend {score.trend}."
        if deps.llm.provider_name != "offline":
            assessment = await _narrate(deps, data, score, label)

    evidence = []
    if data.cgpa is not None:
        evidence.append(
            Evidence(source="Academic Transcript", detail=f"CGPA {data.cgpa:.2f}", quality=EvidenceQuality.DIRECT)
        )
    evidence.append(
        Evidence(
            source="Academic Scoring Engine",
            detail=f"normalized score {score.normalized_score:.1f}/100 ({label})",
            quality=EvidenceQuality.INFERRED,
        )
    )

    result = AcademicResult(
        agent_name=AGENT_NAME,
        status=AgentStatus.SUCCESS if data.cgpa is not None else AgentStatus.WARNING,
        findings=(assessment,),
        evidence=tuple(evidence),
        confidence=0.9 if data.cgpa is not None else 0.3,
        issues=() if data.cgpa is not None else ("CGPA unavailable; academic score defaulted to 0",),
        cgpa=data.cgpa,
        normalized_score=score.normalized_score,
        trend=score.trend,  # type: ignore[arg-type]
        credits_completed=data.credits_completed,
        failed_course_count=len(data.failed_courses),
        consistency=score.consistency,  # type: ignore[arg-type]
        assessment=assessment,
    )

    add_trace(
        trace,
        AGENT_NAME,
        "scoring academic performance",
        TraceStatus.COMPLETED,
        detail=f"score={score.normalized_score:.1f}",
        duration_ms=t["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", f"academic score {score.normalized_score:.1f}/100 ({label})")

    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")
    return {"agent_results": agent_results, "trace": trace, "messages": messages}


async def _narrate(deps: AgentDeps, data: ExtractedApplicationData, score: Any, label: str) -> str:
    context = {
        "cgpa": data.cgpa,
        "normalized_score": score.normalized_score,
        "trend": score.trend,
        "consistency": score.consistency,
        "failed_course_count": len(data.failed_courses),
        "band_label": label,
    }
    try:
        return await deps.llm.complete(_SYSTEM, f"CONTEXT:\n{context}")
    except AgentExecutionError as exc:
        log.warning("agent.academic.narration_failed", error=str(exc))
        return f"{label}: normalized score {score.normalized_score:.1f}/100, trend {score.trend}."
