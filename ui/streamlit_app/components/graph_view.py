"""Render the topology exported by the compiled LangGraph itself."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ui.streamlit_app.components.styling import agent_display_name

_NODE_COLORS = {
    "success": "#d8f3dc",
    "failed": "#f8d7da",
    "skipped": "#eeeeee",
    "pending": "#ffffff",
    "running": "#dbeafe",
}


def topology_to_dot(topology: dict[str, Any], agent_results: dict[str, Any] | None = None) -> str:
    """Convert LangGraph's serialized drawable graph to Graphviz DOT.

    Nodes and edges come only from ``CompiledStateGraph.get_graph``. The UI
    therefore cannot drift away from the executable workflow.
    """

    agent_results = agent_results or {}
    lines = [
        "digraph ScholarAI {",
        'rankdir="TB";',
        'graph [bgcolor="transparent", ranksep="0.32", nodesep="0.16"];',
        'node [shape=box, style="rounded,filled", fontname="Times New Roman", fontsize=9, penwidth=1];',
        'edge [color="#64748b", arrowsize=0.55, penwidth=0.8];',
    ]
    for node in topology.get("nodes", []):
        node_id = str(node.get("id", ""))
        status = str(agent_results.get(node_id, {}).get("status", "pending"))
        fill = _NODE_COLORS.get(status, "#ffffff")
        if node_id in {"__start__", "__end__"}:
            shape = "circle"
            label = "START" if node_id == "__start__" else "END"
            fill = "#e2e8f0"
        elif node_id == "supervisor_plan":
            shape, label, fill = "box", "Supervisor", "#bfdbfe"
        elif node_id == "supervisor_revise":
            shape, label, fill = "box", "Supervisor Revision", "#fde68a"
        elif node_id == "human_review_gate":
            shape, label, fill = "diamond", "Human Review", "#fed7aa"
        else:
            shape, label = "box", agent_display_name(node_id)
        safe_label = label.replace('"', "'")
        lines.append(f'"{node_id}" [shape={shape}, fillcolor="{fill}", label="{safe_label}"];')

    for edge in topology.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        style = 'style="dashed"' if edge.get("conditional") else 'style="solid"'
        lines.append(f'"{source}" -> "{target}" [{style}];')
    lines.append("}")
    return "\n".join(lines)


def render_workflow_graph(topology: dict[str, Any], agent_results: dict[str, Any] | None = None) -> None:
    st.graphviz_chart(topology_to_dot(topology, agent_results), width="stretch")
