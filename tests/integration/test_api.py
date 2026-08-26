"""HTTP-level tests against the real FastAPI app (build spec §19 endpoints)."""

import time

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from scholarai.interfaces.api.app import create_app  # noqa: E402


@pytest.fixture
def client(container):
    app = create_app(container)
    with TestClient(app) as test_client:
        yield test_client


def _wait_for_run(client: TestClient, application_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get(f"/applications/{application_id}/status").json()
        if status["run_status"] in {"completed", "failed", "cancelled"}:
            return status
        time.sleep(0.01)
    raise AssertionError("background evaluation did not finish")


def test_health_reports_offline_provider_and_environment(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "offline"
    assert body["environment"] == "development"


def test_scholarships_lists_all_presets(client):
    response = client.get("/scholarships")
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "merit_scholarship" in codes
    assert "need_based_scholarship" in codes


def test_submit_evaluate_and_decide_round_trip(client):
    transcript = b"Student ID: STU-API-1\nCGPA: 3.7\nCredits Completed: 40\nCurrent Semester: 3\n"
    files = [("files", ("transcript.txt", transcript, "text/plain"))]
    create_response = client.post("/applications", data={"scholarship_code": "merit_scholarship"}, files=files)
    assert create_response.status_code == 200
    application_id = create_response.json()["application_id"]

    evaluate_response = client.post(f"/applications/{application_id}/evaluate")
    assert evaluate_response.status_code == 202
    assert evaluate_response.json()["run_status"] in {"queued", "running"}
    completed = _wait_for_run(client, application_id)
    assert completed["run_status"] == "completed"

    state_response = client.get(f"/applications/{application_id}")
    assert state_response.json()["status"] == "review_required"

    decision_response = client.post(
        f"/applications/{application_id}/human-decision",
        json={"action": "approve", "reviewer": "api-test", "notes": "looks fine"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["final_recommendation"]["final_status"] == "approved"


def test_live_topology_usage_and_log_exports(client):
    create_response = client.post("/applications", data={"scholarship_code": "merit_scholarship"})
    application_id = create_response.json()["application_id"]
    client.post(f"/applications/{application_id}/evaluate")
    _wait_for_run(client, application_id)

    topology = client.get("/applications/workflow/topology")
    assert topology.status_code == 200
    node_ids = {node["id"] for node in topology.json()["graph"]["nodes"]}
    assert {"supervisor_plan", "sop_agent", "human_review_gate"} <= node_ids

    usage = client.get(f"/applications/{application_id}/usage").json()
    assert usage["application_id"] == application_id
    assert usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]
    assert isinstance(usage["events"], list)

    log_download = client.get(f"/applications/{application_id}/logs/download")
    assert log_download.status_code == 200
    assert "attachment" in log_download.headers["content-disposition"]
    assert log_download.json()["trace"]


def test_request_review_starts_a_fresh_supervisor_run(client):
    create_response = client.post("/applications", data={"scholarship_code": "merit_scholarship"})
    application_id = create_response.json()["application_id"]
    client.post(f"/applications/{application_id}/evaluate")
    _wait_for_run(client, application_id)

    response = client.post(
        f"/applications/{application_id}/human-decision",
        json={"action": "request_review", "reviewer": "api-test", "notes": "run again"},
    )
    assert response.status_code == 200
    assert response.json()["runtime"]["run_status"] in {"queued", "running"}
    assert response.json()["final_recommendation"] is None
    assert _wait_for_run(client, application_id)["run_status"] == "completed"

    state = client.get(f"/applications/{application_id}").json()
    planning_events = [event for event in state["trace"] if event["actor"] == "supervisor" and "plan" in event["event"]]
    assert len(planning_events) >= 2


def test_retry_agent_runs_the_agent_and_required_downstream_nodes(client):
    create_response = client.post("/applications", data={"scholarship_code": "merit_scholarship"})
    application_id = create_response.json()["application_id"]
    client.post(f"/applications/{application_id}/evaluate")
    _wait_for_run(client, application_id)

    retry = client.post(
        f"/applications/{application_id}/retry",
        json={"agent_name": "sop_agent"},
    )
    assert retry.status_code == 202
    assert _wait_for_run(client, application_id)["run_status"] == "completed"
    state = client.get(f"/applications/{application_id}").json()
    assert state["plan"] == ["sop_agent", "critic_agent"]
    assert state["sop"]


def test_unknown_application_returns_404(client):
    response = client.get("/applications/APP-DOES-NOT-EXIST")
    assert response.status_code == 404


def test_auth_required_when_api_keys_configured(container):
    container.settings.api.api_keys = ("test-secret-key",)
    app = create_app(container)
    with TestClient(app) as auth_client:
        unauthenticated = auth_client.get("/applications")
        assert unauthenticated.status_code == 401

        authenticated = auth_client.get("/applications", headers={"Authorization": "Bearer test-secret-key"})
        assert authenticated.status_code == 200
