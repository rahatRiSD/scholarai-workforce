from __future__ import annotations

from ui.streamlit_app.services import session


def test_get_client_does_not_mutate_widget_backed_session_state(monkeypatch) -> None:
    state = {"api_base_url": "example.test", "api_key": "secret"}
    monkeypatch.setattr(session.st, "session_state", state)

    client = session.get_client()

    assert state == {"api_base_url": "example.test", "api_key": "secret"}
    assert client.base_url == "http://example.test"


def test_initialize_connection_state_seeds_environment_defaults(monkeypatch) -> None:
    state: dict[str, str] = {}
    monkeypatch.setattr(session.st, "session_state", state)
    monkeypatch.setenv("SCHOLARAI_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("SCHOLARAI_API_KEY", "test-key")

    session.initialize_connection_state()

    assert state == {
        "api_base_url": "https://api.example.test",
        "api_key": "test-key",
    }
