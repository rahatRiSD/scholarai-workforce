"""Token usage and API cost *estimation* for the running Streamlit UI.

Important honesty note: none of the LLM adapters currently return raw
provider usage objects (OpenAI/Anthropic both would, but the ``LLMClient``
port intentionally exposes only the completion text - see
``domain/ports/llm.py`` - to keep provider adapters swappable without leaking
SDK-specific response shapes into agent code). Rather than fabricate precise
numbers, this module estimates tokens from the *character length* of the
prompts and completions the workflow trace actually recorded (~4 characters
per token, a standard rough approximation), and multiplies by each
provider's published per-1K-token pricing. Every number this module produces
is prefixed "estimated" in the UI - it is a planning aid, not a billing
record.
"""

from __future__ import annotations

from typing import Any

CHARS_PER_TOKEN_ESTIMATE = 4.0

# Published per-1K-token list pricing, USD, as of this project's authoring.
# Update alongside `infrastructure/config/settings.py` model defaults if
# those change - this table is deliberately kept in one place.
_PRICING_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    "offline": {"input": 0.0, "output": 0.0},
}

_DEFAULT_PRICING = {"input": 0.001, "output": 0.002}


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / CHARS_PER_TOKEN_ESTIMATE))


def estimate_usage_for_state(state: dict[str, Any], model_name: str) -> dict[str, Any]:
    """Estimates input/output tokens from the recorded trace + agent
    messages + agent findings text, since that's the only text the workflow
    persists that approximates what was actually sent to / returned from an
    LLM."""

    trace = state.get("trace", []) or []
    messages = state.get("messages", []) or []
    agent_results = state.get("agent_results", {}) or {}

    input_chars = 0
    output_chars = 0

    for entry in trace:
        input_chars += len(str(entry.get("event", ""))) + len(str(entry.get("detail", "")))

    for msg in messages:
        output_chars += len(str(msg.get("content", "")))

    for result in agent_results.values():
        output_chars += len(str(result.get("findings", "")))
        for ev in result.get("evidence", []) or []:
            output_chars += len(str(ev.get("detail", "")))

    input_tokens = _estimate_tokens(" " * input_chars)
    output_tokens = _estimate_tokens(" " * output_chars)

    pricing = _PRICING_PER_1K_TOKENS.get(model_name, _DEFAULT_PRICING)
    estimated_cost_usd = (input_tokens / 1000.0) * pricing["input"] + (output_tokens / 1000.0) * pricing["output"]

    return {
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_total_tokens": input_tokens + output_tokens,
        "estimated_cost_usd": round(estimated_cost_usd, 6),
        "pricing_model_used": model_name if model_name in _PRICING_PER_1K_TOKENS else "default-fallback-pricing",
    }
