"""Anthropic adapter for the ``LLMClient`` port."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import anthropic
import structlog
from pydantic import BaseModel

from scholarai.domain.errors import AgentExecutionError
from scholarai.infrastructure.llm.structured import complete_structured_with_repair
from scholarai.infrastructure.llm.usage import usage_ledger

if TYPE_CHECKING:
    from scholarai.infrastructure.config.settings import LLMSettings

log = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class AnthropicLLMClient:
    provider_name = "anthropic"

    def __init__(self, settings: LLMSettings, *, client: anthropic.AsyncAnthropic | None = None) -> None:
        self._settings = settings
        self.model_name = settings.anthropic_model
        api_key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key, timeout=settings.request_timeout_seconds)

    async def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        try:
            response = await self._client.messages.create(  # type: ignore[call-overload]
                model=self.model_name,
                max_tokens=self._settings.max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise AgentExecutionError("llm", f"Anthropic request failed: {exc}") from exc
        usage_ledger.record(
            provider=self.provider_name,
            model=self.model_name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        blocks = [block.text for block in response.content if block.type == "text"]
        return "\n".join(blocks)

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
        *,
        temperature: float = 0.1,
    ) -> T:
        json_instruction = "Respond with ONLY a single JSON object, no markdown fences, no prose."

        async def ask(repair: str | None) -> str:
            content = user if repair is None else f"{user}\n\n{repair}"
            try:
                response = await self._client.messages.create(  # type: ignore[call-overload]
                    model=self.model_name,
                    max_tokens=self._settings.max_tokens,
                    temperature=temperature,
                    system=f"{system}\n\n{json_instruction}",
                    messages=[{"role": "user", "content": content}],
                )
            except anthropic.APIError as exc:
                raise AgentExecutionError("llm", f"Anthropic request failed: {exc}") from exc
            usage_ledger.record(
                provider=self.provider_name,
                model=self.model_name,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            blocks = [block.text for block in response.content if block.type == "text"]
            return "\n".join(blocks)

        return await complete_structured_with_repair(agent_name="llm", response_model=response_model, ask=ask)
