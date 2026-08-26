"""Domain-level error types, distinct from framework exceptions."""

from __future__ import annotations


class ScholarAIError(Exception):
    """Base class for all errors raised intentionally by this application."""


class AgentExecutionError(ScholarAIError):
    """A specialist agent failed to produce a usable result.

    Caught by the orchestration layer and turned into a ``failed``
    ``AgentResult`` rather than crashing the whole workflow — see
    ``application.orchestration.graph``.
    """

    def __init__(self, agent_name: str, detail: str) -> None:
        self.agent_name = agent_name
        self.detail = detail
        super().__init__(f"{agent_name}: {detail}")


class DocumentProcessingError(ScholarAIError):
    """A document could not be parsed or read."""


class UnknownScholarshipError(ScholarAIError):
    """The requested scholarship code has no registered preset."""


class ConfigurationError(ScholarAIError):
    """The application is misconfigured (e.g. missing required settings)."""
