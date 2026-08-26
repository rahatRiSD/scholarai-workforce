"""Ports: abstract interfaces the domain/application layers depend on.

Infrastructure adapters implement these ``Protocol``s. Nothing in
``application`` imports a concrete infrastructure class directly — it is
wired through ``composition.py`` — so swapping OpenAI for Ollama, or Qdrant
for an in-memory store, never touches agent code.
"""
