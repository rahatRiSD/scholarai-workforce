import json

import pytest

from scholarai.domain.models.results import AgentStatus, EligibilityResult
from scholarai.infrastructure.llm.offline_client import OfflineLLMClient


@pytest.mark.asyncio
async def test_complete_structured_copies_matching_context_fields():
    client = OfflineLLMClient()
    context = {
        "agent_name": "eligibility_agent",
        "status": "success",
        "eligible": True,
        "score": 91.5,
        "requirements_checked": ["a", "b"],
    }
    user = f"Interpret this.\nCONTEXT:\n{json.dumps(context)}"
    result = await client.complete_structured("system", user, EligibilityResult)
    assert isinstance(result, EligibilityResult)
    assert result.eligible is True
    assert result.score == 91.5
    assert result.status == AgentStatus.SUCCESS


@pytest.mark.asyncio
async def test_complete_structured_fills_missing_fields_with_safe_defaults():
    client = OfflineLLMClient()
    result = await client.complete_structured("system", "no context here", EligibilityResult)
    assert result.eligible is False
    assert result.score == 0.0


@pytest.mark.asyncio
async def test_complete_labels_output_as_offline():
    client = OfflineLLMClient()
    text = await client.complete("system", "user prompt with no json")
    assert "[offline mode]" in text


def test_provider_name_is_offline():
    assert OfflineLLMClient().provider_name == "offline"
