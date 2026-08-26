"""Eligibility Agent (build spec §6).

Numeric/set-membership checks are 100% deterministic
(``domain.services.eligibility_rules``). The LLM is only asked to write a
short plain-language justification over the already-decided verdict — it
cannot flip ``eligible`` or invent a requirement.
"""

from __future__ import annotations

from typing import Any

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.support import add_message, add_trace, timed
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.errors import AgentExecutionError
from scholarai.domain.models.documents import ExtractedApplicationData
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.results import AgentStatus, EligibilityResult
from scholarai.domain.scholarship_presets import get_preset
from scholarai.domain.services.eligibility_rules import check_eligibility
from scholarai.infrastructure.observability import get_logger

AGENT_NAME = "eligibility_agent"
log = get_logger(__name__)

_SYSTEM = (
    "You are the Eligibility Agent. You are given a deterministic eligibility verdict "
    "(already computed in Python) and must write ONE short sentence explaining it in plain "
    "language for a scholarship reviewer. Do not change the verdict, the score, or invent "
    "any requirement not listed."
)


async def run(state: dict[str, Any], deps: AgentDeps) -> dict[str, Any]:
    trace = list(state.get("trace", []))
    messages = list(state.get("messages", []))
    add_trace(trace, AGENT_NAME, "checking eligibility requirements", TraceStatus.STARTED)
    add_message(messages, "supervisor", AGENT_NAME, "verify eligibility against scholarship requirements")

    data = ExtractedApplicationData.model_validate(state["extracted_data"])
    preset = get_preset(state["scholarship_code"])

    async with timed() as t:
        check = check_eligibility(data, preset.requirements)
        score = 100.0 if check.eligible else max(0.0, 100.0 - len(check.failed_requirements) * 25.0)
        findings = [f"eligible={check.eligible}", *check.requirements_checked]
        issues = list(check.failed_requirements) + list(check.missing_data_requirements)
        evidence = [
            Evidence(source="Eligibility Rules Engine", detail=item, quality=EvidenceQuality.INFERRED)
            for item in check.requirements_checked
        ]

        summary = _default_summary(check.eligible, check.failed_requirements)
        if deps.llm.provider_name != "offline":
            summary = await _narrate(deps, check.eligible, check.requirements_checked, check.failed_requirements)

    result = EligibilityResult(
        agent_name=AGENT_NAME,
        status=AgentStatus.SUCCESS if not check.missing_data_requirements else AgentStatus.WARNING,
        findings=(summary, *findings),
        evidence=tuple(evidence),
        confidence=0.95 if not check.missing_data_requirements else 0.6,
        issues=tuple(issues),
        eligible=check.eligible,
        score=score,
        requirements_checked=check.requirements_checked,
        failed_requirements=check.failed_requirements,
    )

    add_trace(
        trace,
        AGENT_NAME,
        "checking eligibility requirements",
        TraceStatus.COMPLETED,
        detail=f"eligible={check.eligible}",
        duration_ms=t["ms"],
    )
    add_message(messages, AGENT_NAME, "supervisor", f"eligible={check.eligible}, score={score:.0f}/100")

    agent_results = dict(state.get("agent_results", {}))
    agent_results[AGENT_NAME] = result.model_dump(mode="json")
    return {
        "eligibility": result.model_dump(mode="json"),
        "agent_results": agent_results,
        "trace": trace,
        "messages": messages,
    }


def _default_summary(eligible: bool, failed: tuple[str, ...]) -> str:
    if eligible:
        return "Student satisfies all deterministic eligibility requirements."
    return f"Student is not eligible: {'; '.join(failed)}"


async def _narrate(deps: AgentDeps, eligible: bool, checked: tuple[str, ...], failed: tuple[str, ...]) -> str:
    context = {"eligible": eligible, "checked": list(checked), "failed": list(failed)}
    try:
        return await deps.llm.complete(_SYSTEM, f"CONTEXT:\n{context}")
    except AgentExecutionError as exc:
        log.warning("agent.eligibility.narration_failed", error=str(exc))
        return _default_summary(eligible, failed)
