"""Provider-neutral, per-application LLM usage accounting."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_application_id: ContextVar[str] = ContextVar("scholarai_application_id", default="unscoped")
_agent_name: ContextVar[str] = ContextVar("scholarai_agent_name", default="unknown")

# USD per one million tokens. Unknown models remain visible with zero cost
# rather than being assigned fabricated pricing.
_PRICING_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
}


class UsageLedger:
    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = {}

    def record(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated: bool = False,
    ) -> None:
        app_id = _application_id.get()
        input_price, output_price = _price_for(model)
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        self._events.setdefault(app_id, []).append(
            {
                "application_id": app_id,
                "agent": _agent_name.get(),
                "provider": provider,
                "model": model,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "total_tokens": int(input_tokens + output_tokens),
                "cost_usd": round(cost, 8),
                "estimated": estimated,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def summary(self, application_id: str) -> dict[str, Any]:
        events = list(self._events.get(application_id, []))
        return {
            "application_id": application_id,
            "input_tokens": sum(e["input_tokens"] for e in events),
            "output_tokens": sum(e["output_tokens"] for e in events),
            "total_tokens": sum(e["total_tokens"] for e in events),
            "cost_usd": round(sum(e["cost_usd"] for e in events), 8),
            "api_calls": len(events),
            "has_estimates": any(e["estimated"] for e in events),
            "events": events,
        }

    def clear(self, application_id: str) -> None:
        self._events.pop(application_id, None)


def _price_for(model: str) -> tuple[float, float]:
    for prefix, price in _PRICING_PER_MILLION.items():
        if model.startswith(prefix):
            return price
    return (0.0, 0.0)


@contextmanager
def usage_scope(application_id: str, agent_name: str) -> Iterator[None]:
    app_token = _application_id.set(application_id)
    agent_token = _agent_name.set(agent_name)
    try:
        yield
    finally:
        _application_id.reset(app_token)
        _agent_name.reset(agent_token)


usage_ledger = UsageLedger()
