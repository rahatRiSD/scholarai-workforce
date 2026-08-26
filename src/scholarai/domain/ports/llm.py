"""The LLM port: every provider adapter (OpenAI, Anthropic, Ollama) implements this.

Agents depend on ``LLMClient`` only — never on ``openai`` or ``anthropic``
types directly — so the provider is a deployment choice, not a code change.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """A chat-completion client that can be asked to return structured JSON."""

    provider_name: str
    model_name: str

    async def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        """Free-form text completion, used for narrative summaries."""
        ...

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
        *,
        temperature: float = 0.1,
    ) -> T:
        """Structured completion validated against a Pydantic model.

        Implementations must retry once on a validation failure by feeding the
        validation error back to the model (see
        ``infrastructure.llm.structured``), and must raise
        ``AgentExecutionError`` rather than returning an invalid object.
        """
        ...
