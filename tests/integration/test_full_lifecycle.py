"""End-to-end: submit an application, run the Supervisor workflow, and record
a human decision - using the real composition root (sqlite + in-memory
Qdrant + offline LLM, since no API key is set in the test environment)."""

import pytest

from scholarai.application.use_cases.apply_human_decision import apply_human_decision
from scholarai.application.use_cases.run_evaluation import run_evaluation
from scholarai.application.use_cases.submit_application import create_application
from scholarai.composition import build_workflow_graph
from scholarai.domain.models.human import HumanAction, HumanDecision

pytestmark = pytest.mark.asyncio

TRANSCRIPT = b"""
ACADEMIC TRANSCRIPT
Student Name: Integration Test Student
Student ID: STU-INT-01
Program: BSc Computer Science
Current Semester: 5
CGPA: 3.88
Credits Completed: 80

Semester 1 GPA: 3.6
Semester 2 GPA: 3.9

Achievements:
- [award] Dean's List (2024)
"""


async def test_full_application_lifecycle_ends_in_a_final_recommendation(container):
    application = create_application(
        container.application_store, container.document_reader, "merit_scholarship", [("transcript.txt", TRANSCRIPT)]
    )
    assert application.status.value == "received"

    graph = build_workflow_graph(container)
    state = await run_evaluation(container.application_store, graph, application.application_id)
    assert state["status"] == "review_required"
    assert state["evaluation"] is not None
    assert not state["errors"]

    decision = HumanDecision(
        application_id=application.application_id, action=HumanAction.APPROVE, reviewer="test-reviewer"
    )
    final_state = await apply_human_decision(
        container.application_store,
        container.episode_repository,
        container.semantic_memory,
        application.application_id,
        decision,
    )
    assert final_state["final_recommendation"]["final_status"] == "approved"

    persisted = await container.episode_repository.get_episode(application.application_id)
    assert persisted is not None
    assert persisted["status"] == "approved"
    assert persisted["human_decision"]["action"] == "approve"


async def test_ineligible_application_is_rejectable(container):
    ineligible_transcript = TRANSCRIPT.replace(b"CGPA: 3.88", b"CGPA: 2.00")
    application = create_application(
        container.application_store,
        container.document_reader,
        "merit_scholarship",
        [("transcript.txt", ineligible_transcript)],
    )
    graph = build_workflow_graph(container)
    state = await run_evaluation(container.application_store, graph, application.application_id)
    assert state["evaluation"]["recommendation"] == "ineligible"

    decision = HumanDecision(application_id=application.application_id, action=HumanAction.REJECT)
    final_state = await apply_human_decision(
        container.application_store,
        container.episode_repository,
        container.semantic_memory,
        application.application_id,
        decision,
    )
    assert final_state["final_recommendation"]["final_status"] == "rejected"
