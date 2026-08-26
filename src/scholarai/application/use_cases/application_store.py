"""In-process store for in-flight workflow state (short-term/working memory).

A scholarship application moves through several HTTP calls — create, upload
documents, evaluate, human-decide — so *something* has to hold the
LangGraph state between requests. For a modular monolith sized for a
laptop/course project (build spec §38: "do not overengineer"), an in-memory
dict inside the single FastAPI process is the right amount of machinery; a
production deployment would swap this for Redis with the same interface.
Anything that must survive a restart (the final recommendation, the audit
trail) is written to PostgreSQL as soon as it exists — see
``application.use_cases.apply_human_decision``.
"""

from __future__ import annotations

from scholarai.application.orchestration.state import ScholarshipState


class ApplicationStore:
    def __init__(self) -> None:
        self._states: dict[str, ScholarshipState] = {}

    def save(self, application_id: str, state: ScholarshipState) -> None:
        self._states[application_id] = state

    def get(self, application_id: str) -> ScholarshipState | None:
        return self._states.get(application_id)

    def all(self) -> list[ScholarshipState]:
        return list(self._states.values())

    def exists(self, application_id: str) -> bool:
        return application_id in self._states
