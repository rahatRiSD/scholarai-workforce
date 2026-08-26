"""The five required tools (build spec §16), each a thin, logged wrapper over a port.

Tools are called directly by agent code rather than through an LLM
tool-calling loop — this system's LLM layer is confined to interpretation
over already-retrieved/computed data (see ``docs/ARCHITECTURE.md`` §Deterministic
vs LLM), so tool invocation itself stays deterministic and auditable. Each
tool is still exposed as a LangChain ``BaseTool`` so it can be introspected,
traced, and — if a future agent needs it — bound to a tool-calling LLM.
"""
