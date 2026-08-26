"""Application layer: agents, orchestration, tools, use cases.

Depends only on ``domain`` and on infrastructure *ports* — never on a
concrete infrastructure class. Concrete adapters are injected via
``composition.py``.
"""
