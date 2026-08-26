from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.services.evidence_scoring import score_evidence_quality


def test_no_evidence_scores_zero():
    assert score_evidence_quality(()) == 0.0


def test_all_direct_evidence_scores_100():
    evidence = tuple(Evidence(source="x", detail="y", quality=EvidenceQuality.DIRECT) for _ in range(3))
    assert score_evidence_quality(evidence) == 100.0


def test_unavailable_evidence_drags_score_down():
    evidence = (
        Evidence(source="a", detail="b", quality=EvidenceQuality.DIRECT),
        Evidence(source="c", detail="d", quality=EvidenceQuality.UNAVAILABLE),
    )
    assert score_evidence_quality(evidence) == 50.0


def test_inferred_evidence_scores_between_direct_and_unavailable():
    evidence = (Evidence(source="a", detail="b", quality=EvidenceQuality.INFERRED),)
    assert score_evidence_quality(evidence) == 60.0
