"""The explainability envelope every agent and every recommendation carries.

Nothing in this system may assert a fact without a citable source. ``Evidence``
is the unit the Critic Agent checks for and the UI renders — a claim with no
evidence is, by construction, not something the system is allowed to make.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceQuality(StrEnum):
    """How directly the evidence supports the claim it's attached to."""

    DIRECT = "direct"
    """Quoted or extracted verbatim from a source document."""

    INFERRED = "inferred"
    """Derived by deterministic calculation from direct evidence."""

    UNAVAILABLE = "unavailable"
    """No supporting evidence could be found — the claim must not be made."""


class Evidence(BaseModel):
    """A single citable fact backing an agent's finding.

    ``source`` names the document or computation (e.g. ``"Academic
    Transcript"``, ``"Scholarship Policy, Section 3.1"``, ``"GPA
    Calculator"``). Agents must never fabricate a source — if nothing was
    retrieved, quality is ``UNAVAILABLE`` and the detail explains why.
    """

    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    quality: EvidenceQuality = EvidenceQuality.DIRECT
    quote: str | None = None
    page_or_section: str | None = None
