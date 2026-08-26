"""Evaluation Agent (build spec §12).

Combines every specialist's component score into one deterministic,
transparent, weighted overall score and a recommendation class — pure
Python (``domain.services.evaluation``), no LLM involved in the numbers.
The LLM only writes the natural-language summary afterward, over the
already-final numbers, exactly as build spec §12 describes ("The LLM may
explain/contextualize the results").
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.application.tools.calculation_tool import calculate_final_evaluation
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.evaluation import ComponentScores
from scholarai.domain.models.explainability import Evidence
from scholarai.domain.scholarship_presets import get_preset
from scholarai.domain.services.evidence_scoring import score_evidence_quality
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "evaluation_agent"
log = get_logger(__name__)

_SYSTEM = (
    "You are the Evaluation Agent for a university scholarship system. You are given the final, "
    "already-computed component scores, overall score, and recommendation. Write a short (3-5 "
    "sentence) explanation of the recommendation citing the specific numbers you were given. Do "
    "not change any number and do not invent evidence."
)


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "combining specialist results", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "combine component scores into a final recommendation")

    application_id = state["application_id"]
    preset = get_preset(state["scholarship_code"])
    agent_results = dict(state.get("agent_results", {}))
    eligibility = state.get("eligibility") or {}
    verification = agent_results.get("verification_agent", {})
    financial = agent_results.get("financial_agent", {})
    academic = agent_results.get("academic_agent", {})
    achievement = agent_results.get("achievement_agent", {})
    policy = agent_results.get("policy_agent", {})

    async with timed() as t:
        all_evidence: list[Evidence] = []
        for result in (eligibility, verification, financial, academic, achievement, policy):
            for item in result.get("evidence", []):
                all_evidence.append(Evidence.model_validate(item))
        evidence_score = score_evidence_quality(tuple(all_evidence))

        scores = ComponentScores(
            academic_performance=academic.get("normalized_score", 0.0),
            eligibility=eligibility.get("score", 0.0),
            financial_need=financial.get("financial_need_score", 0.0),
            achievements=achievement.get("achievement_score", 0.0),
            supporting_evidence=evidence_score,
        )

        extra_reasons: list[str] = []
        if financial.get("needs_human_review"):
            extra_reasons.append("financial information is missing or uncertain")
        if verification.get("conflict_detected"):
            extra_reasons.append("Verification Agent detected a data conflict between documents")
        if policy.get("citations_found", 1) == 0:
            extra_reasons.append("no policy evidence could be retrieved to support this decision")

        evaluation = calculate_final_evaluation(
            application_id,
            scores,
            preset,
            eligibility.get("eligible", False),
            tuple(extra_reasons),
        )

        summary = _default_summary(evaluation)
        if deps.llm.provider_name != "offline":
            summary = await _narrate(deps, evaluation)

    evaluation_dict = evaluation.model_dump(mode="json")
    evaluation_dict["summary"] = summary
    evaluation_dict["evidence"] = [e.model_dump(mode="json") for e in all_evidence]

    add_trace(
        trace,
        AGENT_NAME,
        "combining specialist results",
        TraceStatus.COMPLETED,
        detail=f"overall={evaluation.overall_score:.1f} -> {evaluation.recommendation.value}",
        duration_ms=t["ms"],
    )
    add_message(
        messages,
        AGENT_NAME,
        "supervisor",
        f"overall score {evaluation.overall_score:.1f}/100 -> {evaluation.recommendation.value}",
    )

    return {"evaluation": evaluation_dict, "trace": trace, "messages": messages}


def _default_summary(evaluation: Any) -> str:
    scores = evaluation.component_scores
    return (
        f"Overall score {evaluation.overall_score:.1f}/100 -> {evaluation.recommendation.value.replace('_', ' ')}. "
        f"Academic {scores.academic_performance:.0f}, Eligibility {scores.eligibility:.0f}, "
        f"Financial Need {scores.financial_need:.0f}, Achievements {scores.achievements:.0f}, "
        f"Evidence {scores.supporting_evidence:.0f}."
    )


async def _narrate(deps: AgentDeps, evaluation: Any) -> str:
    context = {
        "overall_score": evaluation.overall_score,
        "recommendation": evaluation.recommendation.value,
        "component_scores": evaluation.component_scores.model_dump(),
        "weights_used": evaluation.weights_used,
        "review_reasons": list(evaluation.review_reasons),
    }
    try:
        return await deps.llm.complete(_SYSTEM, f"CONTEXT:\n{context}")
    except AgentExecutionError as exc:
        log.warning("agent.evaluation.narration_failed", error=str(exc))
        return _default_summary(evaluation)
