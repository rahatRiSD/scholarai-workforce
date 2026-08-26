"""Thin HTTP client the Streamlit UI uses to talk to the ScholarAI FastAPI
backend. Mirrors the reference trading platform's ``ui/streamlit_app/client.py``
pattern: one small wrapper class, no business logic duplicated from the
backend, every method a direct call to one REST endpoint.

Kept dependency-light (``httpx`` only) so the UI process stays a thin
presentation layer over the real API - all scoring, orchestration, and
persistence logic lives server-side.
"""

from __future__ import annotations

import contextlib
import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("SCHOLARAI_API_BASE_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = float(os.environ.get("SCHOLARAI_API_TIMEOUT_SECONDS", "60"))


class ScholarAIAPIError(RuntimeError):
    """Raised when the backend returns a non-2xx response, carrying the
    parsed error detail so the UI can render something useful instead of a
    raw traceback."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"API error {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class ScholarAIClient:
    """Synchronous client - Streamlit's execution model reruns the whole
    script top-to-bottom on every interaction, so an async client would just
    need an event loop wrapper around every call for no benefit."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("SCHOLARAI_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = httpx.request(method, url, headers=self._headers(), timeout=DEFAULT_TIMEOUT, **kwargs)
        except httpx.ConnectError as exc:
            msg = f"could not reach ScholarAI API at {self.base_url} - is `scholarai serve` running?"
            raise ScholarAIAPIError(0, msg) from exc
        if response.status_code >= 400:
            detail = response.text
            with contextlib.suppress(ValueError):
                detail = response.json().get("detail", detail)
            raise ScholarAIAPIError(response.status_code, str(detail))
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # -- health / catalog -------------------------------------------------
    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_scholarships(self) -> list[dict[str, Any]]:
        return self._request("GET", "/scholarships")

    # -- applications -------------------------------------------------------
    def submit_application(self, scholarship_code: str, files: list[tuple[str, bytes, str]]) -> dict[str, Any]:
        multipart = [("files", (name, content, content_type)) for name, content, content_type in files]
        return self._request(
            "POST", "/applications", data={"scholarship_code": scholarship_code}, files=multipart or None
        )

    def list_applications(self) -> list[dict[str, Any]]:
        return self._request("GET", "/applications")

    def get_application(self, application_id: str) -> dict[str, Any]:
        return self._request("GET", f"/applications/{application_id}")

    def evaluate_application(self, application_id: str) -> dict[str, Any]:
        return self._request("POST", f"/applications/{application_id}/evaluate")

    def get_status(self, application_id: str) -> dict[str, Any]:
        return self._request("GET", f"/applications/{application_id}/status")

    def pause_application(self, application_id: str) -> dict[str, Any]:
        return self._request("POST", f"/applications/{application_id}/pause")

    def resume_application(self, application_id: str) -> dict[str, Any]:
        return self._request("POST", f"/applications/{application_id}/resume")

    def cancel_application(self, application_id: str) -> dict[str, Any]:
        return self._request("POST", f"/applications/{application_id}/cancel")

    def retry_agent(self, application_id: str, agent_name: str) -> dict[str, Any]:
        return self._request("POST", f"/applications/{application_id}/retry", json={"agent_name": agent_name})

    def get_agents(self, application_id: str) -> dict[str, Any]:
        return self._request("GET", f"/applications/{application_id}/agents")

    def get_evaluation(self, application_id: str) -> dict[str, Any]:
        return self._request("GET", f"/applications/{application_id}/evaluation")

    def get_evidence(self, application_id: str) -> dict[str, Any]:
        return self._request("GET", f"/applications/{application_id}/evidence")

    def get_execution_logs(self, application_id: str) -> dict[str, Any]:
        return self._request("GET", f"/applications/{application_id}/logs")

    def get_usage(self, application_id: str) -> dict[str, Any]:
        return self._request("GET", f"/applications/{application_id}/usage")

    def get_workflow_topology(self) -> dict[str, Any]:
        return self._request("GET", "/applications/workflow/topology")

    def submit_human_decision(self, application_id: str, action: str, reviewer: str, notes: str) -> dict[str, Any]:
        payload = {"action": action, "reviewer": reviewer, "notes": notes}
        return self._request("POST", f"/applications/{application_id}/human-decision", json=payload)

    # -- dashboard ----------------------------------------------------------
    def dashboard_summary(self) -> dict[str, Any]:
        return self._request("GET", "/dashboard/summary")

    # -- knowledge base -------------------------------------------------------
    def upload_policy_document(self, filename: str, content: bytes, content_type: str) -> dict[str, Any]:
        return self._request("POST", "/knowledge-base/upload", files={"file": (filename, content, content_type)})

    def search_knowledge_base(self, query: str, limit: int = 5) -> dict[str, Any]:
        return self._request("POST", "/knowledge-base/search", json={"query": query, "limit": limit})

    # -- memory ---------------------------------------------------------------
    def student_history(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/memory/{student_id}")

    def search_similar_cases(self, query: str, limit: int = 5) -> dict[str, Any]:
        return self._request("POST", "/memory/search", json={"query": query, "limit": limit})
