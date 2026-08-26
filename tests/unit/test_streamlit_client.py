from ui.streamlit_app.client import ScholarAIClient


class RecordingClient(ScholarAIClient):
    def __init__(self) -> None:
        super().__init__("http://test")
        self.calls = []

    def _request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return {"ok": True}


def test_streamlit_client_wires_live_operator_controls() -> None:
    client = RecordingClient()
    client.pause_application("APP-1")
    client.resume_application("APP-1")
    client.cancel_application("APP-1")
    client.retry_agent("APP-1", "sop_agent")

    assert [(method, path) for method, path, _ in client.calls] == [
        ("POST", "/applications/APP-1/pause"),
        ("POST", "/applications/APP-1/resume"),
        ("POST", "/applications/APP-1/cancel"),
        ("POST", "/applications/APP-1/retry"),
    ]
    assert client.calls[-1][2]["json"] == {"agent_name": "sop_agent"}
