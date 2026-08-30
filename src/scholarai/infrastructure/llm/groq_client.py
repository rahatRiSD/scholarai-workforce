"""Groq adapter using its OpenAI-compatible chat-completions API."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, TypeVar

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from scholarai.domain.errors import AgentExecutionError
from scholarai.infrastructure.llm.structured import complete_structured_with_repair
from scholarai.infrastructure.llm.usage import usage_ledger

if TYPE_CHECKING:
    from scholarai.infrastructure.config.settings import LLMSettings

T = TypeVar("T", bound=BaseModel)


class GroqLLMClient:
    """Real hosted inference through Groq's OpenAI-compatible endpoint."""

    provider_name = "groq"

    def __init__(self, settings: LLMSettings, *, client: AsyncOpenAI | None = None) -> None:
        self._settings = settings
        self.model_name = settings.groq_model
        self._request_lock = asyncio.Lock()
        self._last_request_started = 0.0
        api_key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=settings.groq_base_url,
            timeout=settings.request_timeout_seconds,
        )

    async def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        try:
            await self._throttle()
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
            raise AgentExecutionError("llm", f"Groq request failed: {exc}") from exc
        self._record_usage(response.usage)
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
                {"role": "system", "content": f"{system}\nReturn a valid JSON object only."},
                {"role": "user", "content": user},
            ]
            if repair:
                messages.append({"role": "user", "content": repair})
            try:
                await self._throttle()
                response = await self._client.chat.completions.create(  # type: ignore[call-overload]
                    model=self.model_name,
                    temperature=temperature,
                    max_tokens=self._settings.max_tokens,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except OpenAIError as exc:
                raise AgentExecutionError("llm", f"Groq request failed: {exc}") from exc
            self._record_usage(response.usage)
            return response.choices[0].message.content or ""

        return await complete_structured_with_repair(agent_name="llm", response_model=response_model, ask=ask)

    async def _throttle(self) -> None:
        """Keep requests inside Groq's free-plan requests-per-minute limit."""
        async with self._request_lock:
            interval = self._settings.groq_min_request_interval_seconds
            elapsed = time.monotonic() - self._last_request_started
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
            self._last_request_started = time.monotonic()

    def _record_usage(self, usage: object | None) -> None:
        if usage is None:
            return
        usage_ledger.record(
            provider=self.provider_name,
            model=self.model_name,
            input_tokens=usage.prompt_tokens,  # type: ignore[attr-defined]
            output_tokens=usage.completion_tokens,  # type: ignore[attr-defined]
        )
