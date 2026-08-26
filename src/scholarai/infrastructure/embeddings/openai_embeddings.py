"""OpenAI embeddings adapter — used automatically once ``OPENAI_API_KEY`` is set."""

from __future__ import annotations

from openai import AsyncOpenAI

_DEFAULT_MODEL = "text-embedding-3-small"
_DEFAULT_DIMENSIONS = 1536


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL, dimensions: int = _DEFAULT_DIMENSIONS) -> None:
        self.dimensions = dimensions
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
