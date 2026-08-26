"""Exercises the compiled LangGraph Supervisor workflow end to end, using fakes
for the LLM (offline, deterministic) and the policy retriever (no network/DB)."""

import pytest

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.orchestration.graph import build_graph
from scholarai.application.orchestration.state import new_state
from scholarai.domain.models.documents import Document, DocumentType
from scholarai.domain.ports.vectorstore import RetrievedChunk
from scholarai.infrastructure.llm.offline_client import OfflineLLMClient

TRANSCRIPT = """
ACADEMIC TRANSCRIPT
Student Name: Amina Rahman
Student ID: STU-10001
Program: BSc Computer Science
Current Semester: 6
CGPA: 3.91
Credits Completed: 96

Semester 1 GPA: 3.65
Semester 2 GPA: 3.95

Achievements:
- [award] Dean's List (2024)
"""

LOW_CGPA_TRANSCRIPT = TRANSCRIPT.replace("CGPA: 3.91", "CGPA: 2.20")

CONFLICTING_APPLICATION_FORM = """
SCHOLARSHIP APPLICATION FORM
Student ID: STU-10001
Self-reported CGPA: 3.30
"""


class FakeRetriever:
    async def retrieve(self, query, *, limit=4):
        return [
            RetrievedChunk(
                text="Minimum CGPA for the Academic Merit Scholarship is 3.50.",
                source="Scholarship Policy",
                section="2.2",
                score=0.4,
                metadata={},
            )
        ]


class EmptyRetriever:
    async def retrieve(self, query, *, limit=4):
        return []


class FakeDocumentReader:
    def supports(self, filename):
        return True

    def read(self, filename, content):
        return Document(filename=filename, document_type=DocumentType.TRANSCRIPT, raw_text="", readable=True)


def _deps(retriever=None):
    return AgentDeps(
        llm=OfflineLLMClient(),
        retriever=retriever or FakeRetriever(),
        document_reader=FakeDocumentReader(),
        web_search=None,
    )


def _seed_state(application_id, scholarship_code, documents):
    state = new_state(application_id, scholarship_code)
    state["documents"] = [
        Document(
            filename=name, document_type=DocumentType.TRANSCRIPT, raw_text=text, readable=True, page_count=1
        ).model_dump(mode="json")
        for name, text in documents
    ]
    return state


@pytest.mark.asyncio
async def test_strong_application_reaches_human_review_with_a_pass():
    graph = build_graph(_deps(), max_critic_revisions=2)
    state = _seed_state("APP-T1", "merit_scholarship", [("transcript.pdf", TRANSCRIPT)])

    final_state = await graph.ainvoke(state)

    assert final_state["status"] == "review_required"
    assert not final_state["errors"]
    assert final_state["evaluation"]["recommendation"] in ("highly_recommended", "recommended")
    assert final_state["critic_result"]["verdict"] == "pass"
    assert final_state["critic_revisions"] == 0


@pytest.mark.asyncio
async def test_low_cgpa_is_ineligible():
    graph = build_graph(_deps(), max_critic_revisions=2)
    state = _seed_state("APP-T2", "merit_scholarship", [("transcript.pdf", LOW_CGPA_TRANSCRIPT)])

    final_state = await graph.ainvoke(state)

    assert final_state["evaluation"]["recommendation"] == "ineligible"
    assert final_state["eligibility"]["eligible"] is False


@pytest.mark.asyncio
async def test_conflicting_cgpa_triggers_revise_loop_and_still_terminates():
    graph = build_graph(_deps(), max_critic_revisions=2)
    state = _seed_state(
        "APP-T3",
        "merit_scholarship",
        [("transcript.pdf", TRANSCRIPT), ("application_form.pdf", CONFLICTING_APPLICATION_FORM)],
    )

    final_state = await graph.ainvoke(state)

    assert final_state["status"] == "review_required"
    assert final_state["critic_revisions"] >= 1
    assert final_state["critic_revisions"] <= 2  # bounded, never loops forever
    assert any("CONFLICT DETECTED" in c for c in final_state["conflicts"])


@pytest.mark.asyncio
async def test_no_policy_evidence_still_completes_and_is_flagged():
    graph = build_graph(_deps(retriever=EmptyRetriever()), max_critic_revisions=2)
    state = _seed_state("APP-T4", "merit_scholarship", [("transcript.pdf", TRANSCRIPT)])

    final_state = await graph.ainvoke(state)

    assert final_state["status"] == "review_required"
    policy_result = final_state["agent_results"]["policy_agent"]
    assert policy_result["citations_found"] == 0
    assert "unavailable" in policy_result["evidence"][0]["quality"]


@pytest.mark.asyncio
async def test_achievement_agent_is_skipped_when_no_achievements_found():
    no_achievements_transcript = TRANSCRIPT.split("\nAchievements:")[0]
    graph = build_graph(_deps(), max_critic_revisions=2)
    state = _seed_state("APP-T5", "merit_scholarship", [("transcript.pdf", no_achievements_transcript)])

    final_state = await graph.ainvoke(state)

    assert "achievement_agent" not in final_state["plan"]
    assert "achievement_agent" not in final_state["agent_results"]
