"""Small shared helpers every agent node uses: timing, tracing, messaging.

All three operate on plain lists (not the state dict) so an agent can build
its trace/messages incrementally across several steps before returning a
single partial-state update — see any module in this package for the usual
shape: ``trace = list(state.get("trace", [])); trace.append(...); ...``.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from scholarai.application.orchestration.trace import TraceStatus, event, message


def add_trace(
    trace: list[dict[str, Any]],
    actor: str,
    description: str,
    status: TraceStatus,
    detail: str = "",
    duration_ms: float | None = None,
) -> list[dict[str, Any]]:
    trace.append(event(actor, description, status, detail, duration_ms).model_dump(mode="json"))
    return trace


def add_message(messages: list[dict[str, Any]], from_agent: str, to_agent: str, content: str) -> list[dict[str, Any]]:
    messages.append(message(from_agent, to_agent, content).model_dump(mode="json"))
    return messages


@asynccontextmanager
async def timed() -> AsyncIterator[dict[str, float]]:
    """Usage: ``async with timed() as t: ... ; t["ms"]`` — duration in milliseconds."""
    holder: dict[str, float] = {"start": time.perf_counter()}
    try:
        yield holder
    finally:
        holder["ms"] = round((time.perf_counter() - holder["start"]) * 1000, 1)
