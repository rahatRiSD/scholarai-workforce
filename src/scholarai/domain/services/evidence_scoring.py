"""Deterministic scoring of evidence quality across all specialist findings."""

from __future__ import annotations

from scholarai.domain.models.explainability import Evidence, EvidenceQuality

_QUALITY_WEIGHT = {
    EvidenceQuality.DIRECT: 1.0,
    EvidenceQuality.INFERRED: 0.6,
    EvidenceQuality.UNAVAILABLE: 0.0,
}


def score_evidence_quality(evidence: tuple[Evidence, ...]) -> float:
    """0-100: how much of the collected evidence is directly sourced vs missing."""
    if not evidence:
        return 0.0
    total_weight = sum(_QUALITY_WEIGHT[item.quality] for item in evidence)
    return round(min(100.0, total_weight / len(evidence) * 100.0), 2)
