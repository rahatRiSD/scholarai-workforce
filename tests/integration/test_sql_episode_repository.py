import pytest

pytestmark = pytest.mark.asyncio


async def test_save_and_get_episode_round_trips(container):
    record = {
        "student_id": "STU-1",
        "scholarship_code": "merit_scholarship",
        "status": "approved",
        "overall_score": 88.5,
        "recommendation": "highly_recommended",
        "agent_findings": {"academic_agent": {"status": "success"}},
        "policy_evidence": [],
        "evaluation": {"overall_score": 88.5},
        "critic_feedback": {"verdict": "pass"},
        "human_decision": {"action": "approve"},
        "timeline": [],
    }
    await container.episode_repository.save_episode("APP-0001", record)

    fetched = await container.episode_repository.get_episode("APP-0001")
    assert fetched is not None
    assert fetched["student_id"] == "STU-1"
    assert fetched["overall_score"] == 88.5
    assert fetched["status"] == "approved"


async def test_get_episode_returns_none_when_missing(container):
    assert await container.episode_repository.get_episode("APP-DOES-NOT-EXIST") is None


async def test_list_episodes_filters_by_student(container):
    await container.episode_repository.save_episode(
        "APP-A", {"student_id": "STU-A", "scholarship_code": "merit_scholarship", "status": "approved"}
    )
    await container.episode_repository.save_episode(
        "APP-B", {"student_id": "STU-B", "scholarship_code": "merit_scholarship", "status": "rejected"}
    )

    only_a = await container.episode_repository.list_episodes(student_id="STU-A")
    assert len(only_a) == 1
    assert only_a[0]["application_id"] == "APP-A"


async def test_save_human_decision_updates_episode_status(container):
    await container.episode_repository.save_episode(
        "APP-C", {"student_id": "STU-C", "scholarship_code": "merit_scholarship", "status": "processing"}
    )
    await container.episode_repository.save_human_decision(
        "APP-C", {"action": "approve", "reviewer": "jane", "notes": "looks good"}
    )
    episode = await container.episode_repository.get_episode("APP-C")
    assert episode["status"] == "approved"
    assert episode["human_decision"]["reviewer"] == "jane"


async def test_summary_counts_reflect_saved_episodes(container):
    await container.episode_repository.save_episode(
        "APP-D", {"student_id": "STU-D", "scholarship_code": "merit_scholarship", "status": "approved"}
    )
    await container.episode_repository.save_episode(
        "APP-E", {"student_id": "STU-E", "scholarship_code": "merit_scholarship", "status": "rejected"}
    )
    counts = await container.episode_repository.summary_counts()
    assert counts["total"] >= 2
    assert counts["approved"] >= 1
    assert counts["rejected"] >= 1
