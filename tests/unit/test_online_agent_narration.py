from types import SimpleNamespace

import pytest

from scholarai.application.agents import critic, verification
from scholarai.domain.models.documents import Document, DocumentType


class RecordingOnlineLLM:
    provider_name = "openai"
    model_name = "gpt-4o-mini"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        self.calls.append((system, user))
        return "Provider-authored explanation preserving the deterministic result."


@pytest.mark.asyncio
async def test_verification_agent_uses_online_provider_for_explanation() -> None:
    llm = RecordingOnlineLLM()
    document = Document(
        filename="transcript.txt",
        document_type=DocumentType.TRANSCRIPT,
        raw_text="Student ID: STU-1\nCGPA: 3.80",
        readable=True,
        page_count=1,
    )
    state = {
        "documents": [document.model_dump(mode="json")],
        "extracted_data": {"achievements": [], "documents_missing": []},
        "trace": [],
        "messages": [],
        "agent_results": {},
        "conflicts": [],
    }

    result = await verification.run(state, SimpleNamespace(llm=llm))

    assert len(llm.calls) == 1
    assert result["agent_results"]["verification_agent"]["findings"] == [
        "Provider-authored explanation preserving the deterministic result."
    ]
    assert result["agent_results"]["verification_agent"]["conflict_detected"] is False


@pytest.mark.asyncio
async def test_critic_agent_uses_online_provider_without_changing_verdict() -> None:
    llm = RecordingOnlineLLM()
    state = {
        "application_id": "APP-ONLINE",
        "scholarship_code": "merit_scholarship",
        "evaluation": {
            "component_scores": {
                "academic_performance": 100.0,
                "eligibility": 100.0,
                "financial_need": 100.0,
                "achievements": 100.0,
                "supporting_evidence": 100.0,
            },
            "overall_score": 100.0,
            "recommendation": "highly_recommended",
        },
        "agent_results": {
            "verification_agent": {"conflict_detected": False},
            "policy_agent": {"policy_questions_answered": 4, "citations_found": 4},
        },
        "plan": [],
        "trace": [],
        "messages": [],
    }

    result = await critic.run(state, SimpleNamespace(llm=llm))

    assert len(llm.calls) == 1
    assert result["critic_result"]["verdict"] == "pass"
    assert result["agent_results"]["critic_agent"]["findings"] == (
        "Provider-authored explanation preserving the deterministic result.",
    )
