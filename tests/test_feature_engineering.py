"""Tests for the feature-engineering pipeline.

The feature pipeline is delivered in Phase 4. This placeholder is skipped until
``models/feature_engineering.py`` exists so the suite stays green in the interim.
"""
from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("models.feature_engineering") is None,
    reason="feature_engineering is delivered in Phase 4.",
)


def test_placeholder():  # pragma: no cover - executed only once Phase 4 lands
    from models import feature_engineering  # noqa: F401
