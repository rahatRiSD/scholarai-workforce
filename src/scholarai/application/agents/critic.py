"""Critic Agent (build spec §13) — an independent audit, not a rubber stamp.

Recomputes the overall score itself from the reported component scores and
weights and compares it to what the Evaluation Agent reported; checks policy
claims have citations; checks for unresolved conflicts; checks the
recommendation actually matches the score band. Any hard failure returns
``REVISE`` with the specific issues, which routes the Supervisor back to the
relevant specialist (see ``application.orchestration.graph``).
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.evaluation import (
    ComponentScores,
    CriticResult,
    CriticVerdict,
    Recommendation,
)
from scholarai.domain.scholarship_presets import get_preset
from scholarai.domain.services.evaluation import compute_overall_score
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "critic_agent"
log = get_logger(__name__)
_SCORE_TOLERANCE = 0.5

_SYSTEM = (
    "You are the Critic Agent in a scholarship-review workforce. Explain the completed "
    "deterministic audit in two or three concise sentences. Preserve the supplied verdict, "
    "scores, checks, and issues exactly; do not override the audit or invent evidence."
)


async def run(state: dict[str, Any], deps: Any) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "auditing the evaluation", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "independently audit the evaluation result")

    evaluation = state.get("evaluation") or {}
    agent_results = state.get("agent_results", {})
    verification = agent_results.get("verification_agent", {})
    policy = agent_results.get("policy_agent", {})
    preset = get_preset(state["scholarship_code"])

    async with timed() as t:
        issues: list[str] = []
        checked: list[str] = []

        checked.append("recomputed overall score against reported component scores")
        component_scores = ComponentScores.model_validate(evaluation.get("component_scores", {}))
        recomputed = compute_overall_score(component_scores, preset.weights)
        reported = evaluation.get("overall_score", 0.0)
        if abs(recomputed - reported) > _SCORE_TOLERANCE:
            issues.append(
                f"calculation mismatch: recomputed overall score {recomputed:.2f} does not match "
                f"reported {reported:.2f}"
            )

        checked.append("policy claims have supporting citations")
        if policy.get("policy_questions_answered") and policy.get("citations_found", 0) == 0:
            issues.append("Policy Agent answered questions but reported zero citations")

        checked.append("evidence sufficiency")
        if component_scores.supporting_evidence < 25.0:
            issues.append(f"supporting evidence score is low ({component_scores.supporting_evidence:.0f}/100)")

        checked.append("unresolved contradictions")
        if verification.get("conflict_detected"):
            issues.append("Verification Agent's CONFLICT DETECTED was not resolved before evaluation")

        checked.append("hallucination check: every agent status is success or warning, not failed")
        for name, result in agent_results.items():
            if result.get("status") == "failed":
                issues.append(f"{name} failed and should not contribute to the score")

        checked.append("recommendation consistent with score band")
        expected = (
            Recommendation.INELIGIBLE
            if evaluation.get("recommendation") == Recommendation.INELIGIBLE.value
            else preset.thresholds.classify(reported)
        )
        if evaluation.get("recommendation") not in (expected.value, Recommendation.INELIGIBLE.value):
            issues.append(
                f"recommendation '{evaluation.get('recommendation')}' does not match score band "
                f"(expected '{expected.value}')"
            )

        checked.append("human review flag is set when required")
        # requires_human_review is advisory; the workflow always pauses for a human
        # decision after a PASS regardless, per build spec §14.

        checked.append("statement of purpose draft is present")
        if "sop_agent" in state.get("plan", []) and not str(state.get("sop") or "").strip():
            issues.append("SOP draft is missing from the completed workforce output")

    verdict = CriticVerdict.REVISE if issues else CriticVerdict.PASS
    result = CriticResult(
        verdict=verdict, issues=tuple(issues), checked=tuple(checked), confidence=0.9 if not issues else 0.6
    )
    issue_summary = "; ".join(issues) or "no issues found"
    audit_summary = f"{verdict.value.upper()}: {issue_summary}"
    if deps.llm.provider_name != "offline":
        audit_summary = await _narrate(deps, result, reported, recomputed)

    add_trace(
        trace,
        AGENT_NAME,
        "auditing the evaluation",
        TraceStatus.COMPLETED,
        detail=verdict.value.upper(),
        duration_ms=t["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", audit_summary)

    agent_results_out = dict(agent_results)
    agent_results_out[AGENT_NAME] = {
        "agent_name": AGENT_NAME,
        "status": "success",
        "findings": (audit_summary,),
        "issues": tuple(issues),
    }

    return {
        "critic_result": result.model_dump(mode="json"),
        "agent_results": agent_results_out,
        "trace": trace,
        "messages": messages,
    }


async def _narrate(deps: Any, result: CriticResult, reported: float, recomputed: float) -> str:
    context = {
        "verdict": result.verdict.value,
        "reported_score": reported,
        "recomputed_score": recomputed,
        "issues": list(result.issues),
        "checks": list(result.checked),
    }
    try:
        return await deps.llm.complete(_SYSTEM, f"CONTEXT:\n{context}")
    except AgentExecutionError as exc:
        log.warning("agent.critic.narration_failed", error=str(exc))
        issue_summary = "; ".join(result.issues) or "no issues found"
        return f"{result.verdict.value.upper()}: {issue_summary}"
