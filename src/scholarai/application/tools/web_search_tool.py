"""Tool 3 — Web Search (optional).

Verifies publicly available university information the applicant references
(e.g. a named external award). Configured through ``TAVILY_API_KEY``; when
absent, this degrades to an explicit "unavailable" result rather than
silently doing nothing — build spec §16: "if no API key exists, provide a
graceful fallback."
"""

from __future__ import annotations

from scholarai.domain.ports.web_search import WebSearchClient, WebSearchResult
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


async def search_web(
    client: WebSearchClient | None, query: str, *, application_id: str, max_results: int = 3
) -> list[WebSearchResult]:
    if client is None:
        log.info("tool.web_search.unavailable", application_id=application_id, query=query)
        return []
    results = await client.search(query, max_results=max_results)
    log.info("tool.web_search", application_id=application_id, query=query, results=len(results))
    return results
