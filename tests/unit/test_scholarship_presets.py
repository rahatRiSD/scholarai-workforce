import pytest

from scholarai.domain.scholarship_presets import PRESETS, get_preset


def test_all_presets_have_weights_summing_to_100():
    for preset in PRESETS.values():
        weights = preset.weights.as_dict()
        assert abs(sum(weights.values()) - 100.0) < 0.01


def test_get_preset_returns_matching_code():
    preset = get_preset("merit_scholarship")
    assert preset.code == "merit_scholarship"


def test_get_preset_raises_on_unknown_code():
    with pytest.raises(ValueError, match="unknown scholarship code"):
        get_preset("does_not_exist")


def test_recommendation_thresholds_are_ordered():
    for preset in PRESETS.values():
        t = preset.thresholds
        assert t.highly_recommended_min > t.recommended_min > t.review_required_min
