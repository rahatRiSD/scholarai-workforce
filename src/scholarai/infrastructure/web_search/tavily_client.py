"""Tavily adapter for the optional web-search tool."""

from __future__ import annotations

import asyncio

import httpx
from ddgs import DDGS

from scholarai.domain.ports.web_search import WebSearchClient, WebSearchResult
from scholarai.infrastructure.config.settings import WebSearchSettings

_TAVILY_URL = "https://api.tavily.com/search"


class TavilyWebSearchClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, *, max_results: int = 5) -> list[WebSearchResult]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _TAVILY_URL,
                json={"api_key": self._api_key, "query": query, "max_results": max_results},
            )
            response.raise_for_status()
            payload = response.json()
        return [
            WebSearchResult(title=item.get("title", ""), url=item.get("url", ""), snippet=item.get("content", ""))
            for item in payload.get("results", [])
        ]


class DuckDuckGoWebSearchClient:
    """No-key public web-search adapter used by default."""

    async def search(self, query: str, *, max_results: int = 5) -> list[WebSearchResult]:
        def run() -> list[dict]:
            return list(DDGS().text(query, max_results=max_results))

        items = await asyncio.to_thread(run)
        return [
            WebSearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("href", item.get("url", ""))),
                snippet=str(item.get("body", item.get("snippet", ""))),
            )
            for item in items
        ]


def build_web_search_client(settings: WebSearchSettings) -> WebSearchClient | None:
    if not settings.enabled:
        return None
    if settings.provider.lower() == "tavily" and settings.tavily_api_key is not None:
        return TavilyWebSearchClient(settings.tavily_api_key.get_secret_value())
    return DuckDuckGoWebSearchClient()
