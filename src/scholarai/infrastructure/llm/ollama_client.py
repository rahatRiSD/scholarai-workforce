"""Ollama adapter for the ``LLMClient`` port — local, free, no API key required."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import httpx
import structlog
from pydantic import BaseModel

from scholarai.domain.errors import AgentExecutionError
from scholarai.infrastructure.llm.structured import complete_structured_with_repair
from scholarai.infrastructure.llm.usage import usage_ledger

if TYPE_CHECKING:
    from scholarai.infrastructure.config.settings import LLMSettings

log = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class OllamaLLMClient:
    provider_name = "ollama"

    def __init__(self, settings: LLMSettings, *, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self.model_name = settings.ollama_model
        self._client = client or httpx.AsyncClient(
            base_url=settings.ollama_base_url, timeout=settings.request_timeout_seconds
        )

    async def _chat(self, system: str, user: str, *, json_mode: bool, temperature: float) -> str:
        payload = {
            "model": self.model_name,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["format"] = "json"
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentExecutionError(
                "llm",
                f"Ollama request failed ({exc}); is `ollama serve` running and is '{self.model_name}' pulled?",
            ) from exc
        payload_out = response.json()
        usage_ledger.record(
            provider=self.provider_name,
            model=self.model_name,
            input_tokens=int(payload_out.get("prompt_eval_count", 0)),
            output_tokens=int(payload_out.get("eval_count", 0)),
        )
        return payload_out.get("message", {}).get("content", "")

    async def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        return await self._chat(system, user, json_mode=False, temperature=temperature)

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
        *,
        temperature: float = 0.1,
    ) -> T:
        async def ask(repair: str | None) -> str:
            content = user if repair is None else f"{user}\n\n{repair}"
            return await self._chat(system, content, json_mode=True, temperature=temperature)

        return await complete_structured_with_repair(agent_name="llm", response_model=response_model, ask=ask)
