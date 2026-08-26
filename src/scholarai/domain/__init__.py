"""Domain layer: entities, value objects, deterministic services, and ports.

Zero third-party runtime dependencies beyond Pydantic. Nothing here imports
LangGraph, LangChain, FastAPI, SQLAlchemy, or any LLM SDK — those belong to
`application` and `infrastructure`. This is what keeps the scoring and
eligibility logic testable without a network connection or a database.
"""
