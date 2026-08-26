"""The Supervisor Agent's planning and routing logic (build spec §4.1).

The Supervisor is not a LangGraph node that "does the work" — it decides
*what work happens*: it builds the initial plan, and on a Critic REVISE it
decides which specialist(s) need to re-run based on the specific issues
raised, rather than blindly restarting the whole pipeline. The actual
routing is wired into edges in ``application.orchestration.graph``; this
module holds the decision logic so it's unit-testable on its own.
"""

from __future__ import annotations

from scholarai.domain.scholarship_presets import ScholarshipPreset

FULL_PLAN = (
    "document_agent",
    "eligibility_agent",
    "academic_agent",
    "financial_agent",
    "achievement_agent",
    "policy_agent",
    "verification_agent",
    "evaluation_agent",
    "sop_agent",
    "critic_agent",
)

_REVISE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "academic_agent": ("academic", "cgpa", "score band"),
    "financial_agent": ("financial",),
    "achievement_agent": ("achievement",),
    "policy_agent": ("policy", "citation"),
    "eligibility_agent": ("eligib",),
    "verification_agent": ("conflict", "contradiction"),
    "sop_agent": ("sop", "statement of purpose", "personal statement"),
}


def build_plan(preset: ScholarshipPreset, has_achievements: bool) -> list[str]:
    """Build the ordered specialist plan, skipping agents a scholarship gives zero weight to.

    ``document_agent``, ``verification_agent``, ``evaluation_agent`` and
    ``critic_agent`` always run — they're structural, not scored components.
    This is the "Supervisor should be capable of skipping unnecessary agents"
    requirement (build spec §17) made concrete.
    """
    plan = ["document_agent", "eligibility_agent"]
    if preset.weights.academic_performance > 0:
        plan.append("academic_agent")
    if preset.weights.financial_need > 0:
        plan.append("financial_agent")
    if preset.weights.achievements > 0 and has_achievements:
        plan.append("achievement_agent")
    plan += ["policy_agent", "verification_agent", "evaluation_agent", "sop_agent", "critic_agent"]
    return plan


def choose_revise_targets(issues: tuple[str, ...]) -> list[str]:
    """Map Critic issues to the specialist(s) that should re-run.

    Falls back to re-running the Evaluation Agent alone when no issue text
    matches a known specialist — most REVISE causes are about how the
    numbers were combined, not about a single specialist's inputs.
    """
    targets: list[str] = []
    haystack = " ".join(issues).lower()
    for agent_name, keywords in _REVISE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            targets.append(agent_name)
    if not targets:
        targets.append("evaluation_agent")
    return targets
