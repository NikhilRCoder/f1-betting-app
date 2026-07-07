"""Tests for the service layer.

Services are delivered from Phase 3 onward. These placeholders are skipped until
the corresponding service modules exist, keeping the suite green in the interim.
"""
from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("services.driver_service") is None,
    reason="Service layer is delivered from Phase 3 onward.",
)


def test_placeholder():  # pragma: no cover - executed only once Phase 3 lands
    from services import driver_service  # noqa: F401
