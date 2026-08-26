"""The nine specialist agents plus the Supervisor's planning logic.

Every agent module exposes a single ``async def run(state, deps) -> dict``
that reads whatever it needs from ``ScholarshipState`` and returns a partial
state update — LangGraph nodes in
``application.orchestration.graph`` are thin wrappers around these
functions, which keeps the agents themselves framework-agnostic and unit
testable without a graph.
"""
