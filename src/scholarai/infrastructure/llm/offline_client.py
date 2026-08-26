"""A deterministic, network-free LLM client.

Used automatically whenever no provider API key is configured (see
``Settings.llm.effective_provider``), so the whole application — including
`scholarai demo` and the test suite — runs with zero setup. This is not a
simulation of an LLM: it never pretends to reason. It copies through the
deterministic values agents already computed and hands back a schema-valid,
clearly-labelled placeholder narrative. Every offline finding is prefixed
so nobody mistakes it for a real model's output.
"""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from scholarai.infrastructure.llm.schema_fill import fill_model
from scholarai.infrastructure.llm.structured import extract_json_object
from scholarai.infrastructure.llm.usage import usage_ledger

T = TypeVar("T", bound=BaseModel)

_OFFLINE_NOTE = (
    "[offline mode] No LLM provider is configured, so this narrative was generated "
    "deterministically from the computed values below rather than by a language model."
)


class OfflineLLMClient:
    provider_name = "offline"
    model_name = "deterministic-template"

    async def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        usage_ledger.record(provider=self.provider_name, model=self.model_name, input_tokens=0, output_tokens=0)
        context = _extract_context(user)
        if context:
            facts = "; ".join(f"{k}={v}" for k, v in list(context.items())[:6])
            return f"{_OFFLINE_NOTE} Key facts: {facts}."
        return _OFFLINE_NOTE

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
        *,
        temperature: float = 0.1,
    ) -> T:
        usage_ledger.record(provider=self.provider_name, model=self.model_name, input_tokens=0, output_tokens=0)
        context = _extract_context(user)
        context = dict(context)
        for narrative_field in ("assessment", "interpretation", "summary"):
            if narrative_field in response_model.model_fields and narrative_field not in context:
                context[narrative_field] = _OFFLINE_NOTE
        if "findings" in response_model.model_fields and "findings" not in context:
            context["findings"] = (_OFFLINE_NOTE,)
        if "confidence" in response_model.model_fields and "confidence" not in context:
            context["confidence"] = 0.5
        instance = fill_model(response_model, context)
        return instance  # type: ignore[return-value]


def _extract_context(user: str) -> dict:
    candidate = extract_json_object(user)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
