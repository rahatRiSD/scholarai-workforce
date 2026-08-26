from ui.streamlit_app.components.graph_view import topology_to_dot
from ui.streamlit_app.components.workflow_controls import control_availability


def test_live_control_states_follow_runtime_status() -> None:
    assert control_availability("running") == {
        "pause": True,
        "resume": False,
        "cancel": True,
        "retry": False,
    }
    assert control_availability("paused")["resume"] is True
    assert control_availability("completed")["retry"] is True
    assert control_availability("cancelled")["retry"] is True


def test_graph_view_renders_only_exported_langgraph_topology() -> None:
    topology = {
        "nodes": [{"id": "__start__"}, {"id": "supervisor_plan"}, {"id": "sop_agent"}],
        "edges": [
            {"source": "__start__", "target": "supervisor_plan"},
            {"source": "supervisor_plan", "target": "sop_agent", "conditional": True},
        ],
    }
    dot = topology_to_dot(topology, {"sop_agent": {"status": "success"}})
    assert '"__start__" -> "supervisor_plan"' in dot
    assert '"supervisor_plan" -> "sop_agent" [style="dashed"]' in dot
    assert "SOP Writer" in dot
