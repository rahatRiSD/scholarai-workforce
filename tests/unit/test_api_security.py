"""API auth logic. Skips cleanly if FastAPI isn't installed in this environment."""

import pytest

fastapi = pytest.importorskip("fastapi")

from scholarai.interfaces.api.security import _matches_any  # noqa: E402


def test_matches_any_true_for_a_configured_key():
    assert _matches_any("secret-123", ("secret-123", "other-key")) is True


def test_matches_any_false_for_unknown_key():
    assert _matches_any("wrong", ("secret-123",)) is False


def test_matches_any_false_with_no_keys_configured():
    assert _matches_any("anything", ()) is False
