"""Deterministic hashing embeddings — the offline/no-API-key default.

A hashed bag of unigrams and bigrams, sign-folded into a fixed number of
dimensions and L2-normalized. It captures lexical overlap only — good enough
for a policy knowledge base of a few dozen short documents, not a general
semantic embedding model. That's a deliberate trade: the RAG pipeline (chunk,
embed, store, retrieve, cite) runs and is testable with zero network and zero
API key, matching build spec §16's "if no API key exists, provide a graceful
fallback." Swapping in a hosted embedding model is a one-line change in
``composition.py``.

Hashing uses blake2b (not the builtin ``hash``, whose seed is randomized per
process) so vectors stay comparable across restarts.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterator
from itertools import pairwise

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'\-.]*")
DEFAULT_DIMENSIONS = 256


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _features(text: str) -> Iterator[str]:
    tokens = _tokens(text)
    yield from tokens
    for earlier, later in pairwise(tokens):
        yield f"{earlier}_{later}"


class HashingEmbedder:
    """Implements ``domain.ports.vectorstore.Embedder`` with zero dependencies."""

    def __init__(self, dimensions: int = DEFAULT_DIMENSIONS) -> None:
        if dimensions < 8:
            msg = f"dimensions must be at least 8, got {dimensions}"
            raise ValueError(msg)
        self.dimensions = dimensions

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for feature in _features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]

    async def embed(self, text: str) -> list[float]:
        return self._embed_one(text)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]
