"""The Supervisor-orchestrated LangGraph workflow (build spec §17).

::

    START -> supervisor_plan -> [dynamic plan: document -> eligibility ->
    academic -> financial -> achievement -> policy -> verification ->
    evaluation] -> critic_agent -> (PASS -> human_review_gate -> END)
                                 -> (REVISE, budget left -> supervisor_revise
                                     -> [re-run targeted specialist(s)] ->
                                     evaluation -> critic_agent -> ...)
                                 -> (REVISE, budget exhausted -> human_review_gate)

The graph pauses — deliberately ends the invocation — at
``human_review_gate`` rather than auto-deciding. "Resuming" after a human
decision is a separate, small, plain-Python finalize step
(``application.use_cases.apply_human_decision``) rather than a second
LangGraph invocation with an interrupt/checkpoint mechanism: with only one
pause point in the whole workflow, a checkpointer buys nothing but another
moving part, and build spec §38 is explicit about not overengineering. The
LangGraph graph itself is still the real, dynamically-routed, feedback-
looping workflow build spec §17 asks for — see ``docs/ARCHITECTURE.md``
for the full rationale.
"""

from __future__ import annotations

from collections.abc import Hashable
from typing import Any

from langgraph.graph import END, START, StateGraph

from scholarai.application.agents import (
    academic_evaluation,
    achievement,
    critic,
    document_analysis,
    eligibility,
    evaluation,
    financial_need,
    policy_rag,
    sop_writer,
    verification,
)
from scholarai.application.agents.deps import AgentDeps
from scholarai.application.agents.supervisor import FULL_PLAN, build_plan, choose_revise_targets
from scholarai.application.agents.support import add_message, add_trace
from scholarai.application.orchestration.state import ScholarshipState
from scholarai.application.orchestration.trace import TraceStatus
from scholarai.domain.scholarship_presets import get_preset
from scholarai.infrastructure.llm.usage import usage_scope
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)

_AGENT_MODULES = {
    "document_agent": document_analysis,
    "eligibility_agent": eligibility,
    "academic_agent": academic_evaluation,
    "financial_agent": financial_need,
    "achievement_agent": achievement,
    "policy_agent": policy_rag,
    "verification_agent": verification,
    "evaluation_agent": evaluation,
    "sop_agent": sop_writer,
    "critic_agent": critic,
}
_SPECIALIST_NODE_MAP: dict[Hashable, str] = {name: name for name in _AGENT_MODULES}


def _supervisor_plan_node_factory():
    async def supervisor_plan(state: ScholarshipState) -> dict[str, Any]:
        trace = list(state.get("trace", []))
        messages = list(state.get("messages", []))
        add_trace(trace, "supervisor", "understanding objective and creating execution plan", TraceStatus.STARTED)

        preset = get_preset(state["scholarship_code"])
        # Achievement presence isn't known yet (documents haven't been read) - the plan
        # starts optimistic (includes achievement_agent whenever the scholarship weights
        # it at all) and _document_agent_node below drops it if the Document Analysis
        # Agent finds nothing to evaluate. This is the "skip unnecessary agents /
        # re-plan once more is known" behaviour from build spec §17, made concrete.
        requested_plan = list(state.get("requested_plan", []))
        plan = requested_plan or build_plan(preset, has_achievements=True)

        add_trace(
            trace,
            "supervisor",
            "understanding objective and creating execution plan",
            TraceStatus.COMPLETED,
            detail=f"plan: {' -> '.join(plan)}",
        )
        add_message(messages, "supervisor", "supervisor", f"execution plan: {', '.join(plan)}")

        return {
            "plan": plan,
            "requested_plan": [],
            "current_step": 0,
            "status": "processing",
            "trace": trace,
            "messages": messages,
        }

    return supervisor_plan


def _specialist_node_factory(agent_name: str, deps: AgentDeps):
    module = _AGENT_MODULES[agent_name]

    async def node(state: ScholarshipState) -> dict[str, Any]:
        try:
            with usage_scope(state["application_id"], agent_name):
                result = await module.run(dict(state), deps)
        except Exception as exc:  # noqa: BLE001 - an agent failure must not crash the workflow
            log.error("orchestration.agent_failed", agent=agent_name, error=str(exc))
            errors = list(state.get("errors", []))
            errors.append(f"{agent_name} failed: {exc}")
            trace = list(state.get("trace", []))
            add_trace(trace, agent_name, "processing", TraceStatus.FAILED, detail=str(exc))
            agent_results = dict(state.get("agent_results", {}))
            agent_results[agent_name] = {
                "agent_name": agent_name,
                "status": "failed",
                "findings": (),
                "evidence": (),
                "confidence": 0.0,
                "issues": (f"agent raised an exception: {exc}",),
            }
            result = {"errors": errors, "trace": trace, "agent_results": agent_results}

        if agent_name == "document_agent":
            result = _drop_achievement_agent_if_unneeded(state, result)

        result["current_step"] = state.get("current_step", 0) + 1
        return result

    return node


def _drop_achievement_agent_if_unneeded(state: ScholarshipState, result: dict[str, Any]) -> dict[str, Any]:
    """Re-plan after seeing the extracted data: no achievements found -> skip that agent.

    Mutating the plan mid-flight (rather than only at the start) is what makes
    "the Supervisor should be capable of skipping unnecessary agents" (build
    spec §17) a runtime decision instead of a static, pre-computed list.
    """
    extracted = result.get("extracted_data")
    achievements = extracted.get("achievements") if extracted else None
    plan = list(state.get("plan", []))
    if not achievements and "achievement_agent" in plan:
        plan.remove("achievement_agent")
        result = {**result, "plan": plan}
    return result


def _route_to_first_step(state: ScholarshipState) -> str:
    plan = state.get("plan") or list(FULL_PLAN)
    return plan[0] if plan else "evaluation_agent"


def _route_within_plan(state: ScholarshipState) -> str:
    plan = state.get("plan", [])
    step = state.get("current_step", 0)
    if step < len(plan):
        return plan[step]
    return "critic_agent"


def _route_after_critic_factory(max_revisions: int):
    def route_after_critic(state: ScholarshipState) -> str:
        critic_result = state.get("critic_result") or {}
        revisions = state.get("critic_revisions", 0)
        if critic_result.get("verdict") == "pass":
            return "human_review_gate"
        if revisions >= max_revisions:
            return "human_review_gate"
        return "supervisor_revise"

    return route_after_critic


def _supervisor_revise_node_factory():
    async def supervisor_revise(state: ScholarshipState) -> dict[str, Any]:
        trace = list(state.get("trace", []))
        messages = list(state.get("messages", []))
        critic_result = state.get("critic_result") or {}
        issues = tuple(critic_result.get("issues", []))
        targets = choose_revise_targets(issues)
        revise_plan = [*dict.fromkeys(targets), "evaluation_agent", "critic_agent"]

        add_trace(
            trace,
            "supervisor",
            "routing revision based on critic feedback",
            TraceStatus.INFO,
            detail=f"re-running: {', '.join(revise_plan)}",
        )
        add_message(
            messages,
            "critic_agent",
            "supervisor",
            f"REVISE: {'; '.join(issues) or 'issues found'}",
        )
        add_message(messages, "supervisor", "workflow", f"re-running {', '.join(revise_plan)}")

        return {
            "plan": revise_plan,
            "current_step": 0,
            "critic_revisions": state.get("critic_revisions", 0) + 1,
            "trace": trace,
            "messages": messages,
        }

    return supervisor_revise


def _human_review_gate_node_factory():
    async def human_review_gate(state: ScholarshipState) -> dict[str, Any]:
        trace = list(state.get("trace", []))
        add_trace(trace, "supervisor", "awaiting human decision", TraceStatus.WAITING)
        return {"status": "review_required", "trace": trace}

    return human_review_gate


def build_graph(deps: AgentDeps, *, max_critic_revisions: int = 2):
    """Compile the LangGraph Supervisor workflow. Call once per process; reuse the compiled graph."""
    builder = StateGraph(ScholarshipState)

    builder.add_node("supervisor_plan", _supervisor_plan_node_factory())
    for agent_name in _AGENT_MODULES:
        builder.add_node(agent_name, _specialist_node_factory(agent_name, deps))
    builder.add_node("supervisor_revise", _supervisor_revise_node_factory())
    builder.add_node("human_review_gate", _human_review_gate_node_factory())

    builder.add_edge(START, "supervisor_plan")
    builder.add_conditional_edges("supervisor_plan", _route_to_first_step, _SPECIALIST_NODE_MAP)

    non_critic_agents = [name for name in _AGENT_MODULES if name != "critic_agent"]
    for agent_name in non_critic_agents:
        builder.add_conditional_edges(agent_name, _route_within_plan, _SPECIALIST_NODE_MAP)

    critic_routes: dict[Hashable, str] = {
        "human_review_gate": "human_review_gate",
        "supervisor_revise": "supervisor_revise",
    }
    builder.add_conditional_edges(
        "critic_agent",
        _route_after_critic_factory(max_critic_revisions),
        critic_routes,
    )
    builder.add_conditional_edges("supervisor_revise", _route_to_first_step, _SPECIALIST_NODE_MAP)
    builder.add_edge("human_review_gate", END)

    return builder.compile()
