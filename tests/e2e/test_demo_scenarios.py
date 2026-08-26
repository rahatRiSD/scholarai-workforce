"""Runs the five synthetic sample applications (build spec §27) through the
real Supervisor workflow, reading the actual files under
``data/sample_applications`` - the same files ``scholarai demo`` uses. Each
case is asserted to land on the workflow path it was designed to
demonstrate. Uses the offline LLM client and an empty policy retriever so
this test needs no network, API key, database, or vector store."""

from pathlib import Path

import pytest

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.orchestration.graph import build_graph
from scholarai.application.orchestration.state import new_state
from scholarai.domain.models.documents import Document
from scholarai.infrastructure.documents.composite import CompositeDocumentReader
from scholarai.infrastructure.llm.offline_client import OfflineLLMClient

pytestmark = pytest.mark.asyncio

_SAMPLE_ROOT = Path(__file__).resolve().parents[2] / "data" / "sample_applications"


class EmptyRetriever:
    async def retrieve(self, query, *, limit=4):
        return []


def _load_case(folder_name: str) -> list[Document]:
    reader = CompositeDocumentReader()
    folder = _SAMPLE_ROOT / folder_name
    documents = []
    for path in sorted(folder.iterdir()):
        documents.append(reader.read(path.name, path.read_bytes()))
    return documents


async def _run(folder_name: str, scholarship_code: str):
    deps = AgentDeps(
        llm=OfflineLLMClient(), retriever=EmptyRetriever(), document_reader=CompositeDocumentReader(), web_search=None
    )
    graph = build_graph(deps, max_critic_revisions=2)
    state = new_state(f"APP-E2E-{folder_name}", scholarship_code)
    state["documents"] = [doc.model_dump(mode="json") for doc in _load_case(folder_name)]
    return await graph.ainvoke(state)


async def test_student_a_strong_academic_is_recommended():
    final_state = await _run("student_a_strong_academic", "merit_scholarship")
    assert not final_state["errors"]
    assert final_state["eligibility"]["eligible"] is True
    assert final_state["evaluation"]["recommendation"] in ("highly_recommended", "recommended")
    assert final_state["status"] == "review_required"


async def test_student_b_missing_financial_document_is_flagged_unknown():
    final_state = await _run("student_b_missing_financial", "merit_scholarship")
    financial = final_state["agent_results"]["financial_agent"]
    assert financial["needs_human_review"] is True
    assert "UNKNOWN / NEEDS HUMAN REVIEW" in financial["findings"]


async def test_student_c_conflicting_cgpa_triggers_conflict_detection():
    final_state = await _run("student_c_conflicting_cgpa", "merit_scholarship")
    assert final_state["conflicts"], "expected the CGPA discrepancy to be caught"
    assert any("CONFLICT DETECTED" in c for c in final_state["conflicts"])


async def test_student_d_ineligible_cgpa_is_marked_ineligible():
    final_state = await _run("student_d_ineligible_cgpa", "merit_scholarship")
    assert final_state["eligibility"]["eligible"] is False
    assert final_state["evaluation"]["recommendation"] == "ineligible"


async def test_student_e_financial_need_scores_high_on_financial_need():
    final_state = await _run("student_e_financial_need", "need_based_scholarship")
    assert final_state["eligibility"]["eligible"] is True
    financial = final_state["agent_results"]["financial_agent"]
    assert financial["financial_need_score"] >= 50.0
