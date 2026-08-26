"""Pure control-state rules shared by the live Streamlit page and tests."""

from __future__ import annotations


def control_availability(run_status: str) -> dict[str, bool]:
    active = {"queued", "running", "paused", "cancelling"}
    return {
        "pause": run_status == "running",
        "resume": run_status == "paused",
        "cancel": run_status in {"queued", "running", "paused"},
        "retry": run_status not in active,
    }
