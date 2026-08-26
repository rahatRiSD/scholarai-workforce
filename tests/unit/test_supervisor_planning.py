from scholarai.application.agents.supervisor import build_plan, choose_revise_targets
from scholarai.domain.scholarship_presets import get_preset


def test_build_plan_includes_all_scored_agents_when_weighted():
    preset = get_preset("merit_scholarship")
    plan = build_plan(preset, has_achievements=True)
    assert plan[0] == "document_agent"
    assert plan[-1] == "critic_agent"
    assert "academic_agent" in plan
    assert "financial_agent" in plan
    assert "achievement_agent" in plan
    assert "policy_agent" in plan
    assert "verification_agent" in plan
    assert "evaluation_agent" in plan


def test_build_plan_is_deterministically_ordered():
    preset = get_preset("merit_scholarship")
    assert build_plan(preset, True) == build_plan(preset, True)


def test_choose_revise_targets_maps_academic_keywords():
    targets = choose_revise_targets(("calculation mismatch: recomputed academic score off",))
    assert "academic_agent" in targets


def test_choose_revise_targets_maps_conflict_keywords_to_verification():
    targets = choose_revise_targets(("Verification Agent's CONFLICT DETECTED was not resolved",))
    assert "verification_agent" in targets


def test_choose_revise_targets_falls_back_to_evaluation_agent():
    targets = choose_revise_targets(("some entirely unrelated issue text",))
    assert targets == ["evaluation_agent"]


def test_choose_revise_targets_can_return_multiple_agents():
    targets = choose_revise_targets(("academic score wrong", "financial data uncertain"))
    assert "academic_agent" in targets
    assert "financial_agent" in targets
