"""OpenAI adapter for the ``LLMClient`` port — the default, easiest-to-configure provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import structlog
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from scholarai.domain.errors import AgentExecutionError
from scholarai.infrastructure.llm.structured import complete_structured_with_repair
from scholarai.infrastructure.llm.usage import usage_ledger

if TYPE_CHECKING:
    from scholarai.infrastructure.config.settings import LLMSettings

log = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class OpenAILLMClient:
    provider_name = "openai"

    def __init__(self, settings: LLMSettings, *, client: AsyncOpenAI | None = None) -> None:
        self._settings = settings
        self.model_name = settings.openai_model
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        self._client = client or AsyncOpenAI(api_key=api_key, timeout=settings.request_timeout_seconds)

    async def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                temperature=temperature,
                max_tokens=self._settings.max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except OpenAIError as exc:
            raise AgentExecutionError("llm", f"OpenAI request failed: {exc}") from exc
        if response.usage:
            usage_ledger.record(
                provider=self.provider_name,
                model=self.model_name,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
        return response.choices[0].message.content or ""

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
        *,
        temperature: float = 0.1,
    ) -> T:
        async def ask(repair: str | None) -> str:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
            if repair:
                messages.append({"role": "user", "content": repair})
            try:
                response = await self._client.chat.completions.create(  # type: ignore[call-overload]
                    model=self.model_name,
                    temperature=temperature,
                    max_tokens=self._settings.max_tokens,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except OpenAIError as exc:
                raise AgentExecutionError("llm", f"OpenAI request failed: {exc}") from exc
            if response.usage:
                usage_ledger.record(
                    provider=self.provider_name,
                    model=self.model_name,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                )
            return response.choices[0].message.content or ""

        return await complete_structured_with_repair(agent_name="llm", response_model=response_model, ask=ask)
