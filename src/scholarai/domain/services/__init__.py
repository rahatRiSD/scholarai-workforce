"""Deterministic domain services.

Every function here is pure Python: no LLM calls, no I/O, no randomness. This
is where "numbers must come from deterministic code" (build spec §24) is
enforced structurally — an LLM client cannot even be imported into this
package without failing a code-review grep for ``openai|anthropic|ollama``.
"""
