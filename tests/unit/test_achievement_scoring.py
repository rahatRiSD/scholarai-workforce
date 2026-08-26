from scholarai.domain.services.achievement_scoring import score_achievements
from tests.unit.factories import make_achievement


def test_no_achievements_scores_zero():
    result = score_achievements(())
    assert result.score == 0.0
    assert result.evaluated == 0


def test_unevidenced_achievement_scores_half_and_is_flagged():
    evidenced = score_achievements((make_achievement(evidence_document="cert.pdf"),))
    unevidenced = score_achievements((make_achievement(evidence_document=None),))
    assert unevidenced.score == evidenced.score / 2
    assert unevidenced.unevidenced == ("Dean's List",)


def test_score_caps_at_100():
    many = tuple(make_achievement(title=f"Award {i}", category="publication") for i in range(10))
    result = score_achievements(many)
    assert result.score == 100.0


def test_categories_are_deduplicated_preserving_order():
    achievements = (
        make_achievement(category="award", title="A"),
        make_achievement(category="award", title="B"),
        make_achievement(category="leadership", title="C"),
    )
    result = score_achievements(achievements)
    assert result.categories == ("award", "leadership")
