"""Port for optional public web search (e.g. verifying public university info)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str


class WebSearchClient(Protocol):
    async def search(self, query: str, *, max_results: int = 5) -> list[WebSearchResult]: ...
