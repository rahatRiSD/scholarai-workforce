import pytest

from scholarai.infrastructure.llm.usage import UsageLedger, usage_scope


def test_usage_ledger_uses_actual_provider_counts_and_agent_scope() -> None:
    ledger = UsageLedger()
    with usage_scope("APP-USAGE", "sop_agent"):
        ledger.record(provider="openai", model="gpt-4o-mini", input_tokens=1_000, output_tokens=500)

    summary = ledger.summary("APP-USAGE")
    assert summary["input_tokens"] == 1_000
    assert summary["output_tokens"] == 500
    assert summary["total_tokens"] == 1_500
    assert summary["cost_usd"] == pytest.approx(0.00045)
    assert summary["events"][0]["agent"] == "sop_agent"
