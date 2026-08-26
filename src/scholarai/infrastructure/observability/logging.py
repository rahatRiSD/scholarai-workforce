"""Structured logging setup, with a redaction processor for student privacy.

Build spec §23 (Privacy & Security) is explicit: don't log full documents or
unnecessary personal information. ``_redact`` strips a fixed set of sensitive
keys from every log event before it's rendered, so a stray ``log.info(...,
raw_text=doc.raw_text)`` upstream can't leak a transcript into stdout — the
key is dropped here regardless of who logged it.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_SENSITIVE_KEYS = {
    "raw_text",
    "full_name",
    "family_income_annual",
    "household_size",
    "tuition_cost_annual",
    "financial_aid_already_received",
    "quote",
}
_MAX_STRING_LENGTH = 300


def _redact(_logger: object, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict.keys()):
        if key in _SENSITIVE_KEYS:
            event_dict[key] = "<redacted>"
            continue
        value = event_dict[key]
        if isinstance(value, str) and len(value) > _MAX_STRING_LENGTH:
            event_dict[key] = value[:_MAX_STRING_LENGTH] + "...<truncated>"
    return event_dict


def configure_logging(level: str = "INFO", *, json_output: bool = False) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact,
    ]
    renderer = structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "scholarai") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
