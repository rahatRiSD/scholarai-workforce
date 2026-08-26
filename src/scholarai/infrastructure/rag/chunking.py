"""Splits a policy document's text into citable chunks.

Chunks track the most recent Markdown heading (``##``/``###``) as a
``section`` label, which is what lets the Policy Agent cite
"Scholarship Policy, Section 3.1" rather than an opaque chunk index.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_TARGET_CHUNK_CHARS = 800
_MIN_CHUNK_CHARS = 40


@dataclass(frozen=True)
class Chunk:
    text: str
    section: str | None
    index: int


def chunk_document(text: str) -> list[Chunk]:
    lines = text.splitlines()
    chunks: list[Chunk] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        content = "\n".join(buffer).strip()
        if len(content) >= _MIN_CHUNK_CHARS:
            chunks.append(Chunk(text=content, section=current_section, index=len(chunks)))
        buffer.clear()

    for line in lines:
        heading = _HEADING_RE.match(line.strip())
        if heading:
            flush()
            current_section = heading.group(2).strip()
            buffer.append(line)
            continue
        buffer.append(line)
        if sum(len(b) for b in buffer) >= _TARGET_CHUNK_CHARS:
            flush()

    flush()
    if not chunks and text.strip():
        chunks.append(Chunk(text=text.strip(), section=None, index=0))
    return chunks
