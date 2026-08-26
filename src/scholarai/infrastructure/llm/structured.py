"""Shared helper for validating an LLM's JSON reply against a Pydantic model.

Every provider client calls ``parse_or_repair`` rather than hand-rolling its
own retry loop, so all three providers fail and recover identically.
"""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from scholarai.domain.errors import AgentExecutionError

T = TypeVar("T", bound=BaseModel)


def extract_json_object(text: str) -> str:
    """Best-effort extraction of a JSON object from a possibly-chatty reply."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return text
    return text[start : end + 1]


def parse_structured(raw_text: str, response_model: type[T]) -> T:
    candidate = extract_json_object(raw_text)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        msg = f"model did not return valid JSON: {exc}"
        raise ValueError(msg) from exc
    return response_model.model_validate(data)


def repair_prompt(response_model: type[T], detail: str) -> str:
    schema = json.dumps(response_model.model_json_schema(), indent=2)
    return (
        "Your previous response was not valid for the required schema.\n"
        f"Validation error: {detail}\n\n"
        f"Return ONLY a JSON object matching this schema, no prose, no markdown fences:\n{schema}"
    )


async def complete_structured_with_repair(
    *,
    agent_name: str,
    response_model: type[T],
    ask: object,  # a zero-or-one-arg async callable, typed loosely to avoid a cycle
) -> T:
    """Call ``ask()`` for the first attempt, then ``ask(repair_text)`` once on failure.

    ``ask`` is an async callable accepting an optional extra instruction
    string and returning the raw model text. Kept generic so OpenAI/
    Anthropic/Ollama clients can share this retry policy without sharing an
    HTTP client type.
    """
    first_raw = await ask(None)  # type: ignore[operator]
    try:
        return parse_structured(first_raw, response_model)
    except (ValueError, ValidationError) as first_error:
        repair = repair_prompt(response_model, str(first_error))
        second_raw = await ask(repair)  # type: ignore[operator]
        try:
            return parse_structured(second_raw, response_model)
        except (ValueError, ValidationError) as second_error:
            raise AgentExecutionError(
                agent_name, f"LLM returned invalid structured output twice: {second_error}"
            ) from second_error
