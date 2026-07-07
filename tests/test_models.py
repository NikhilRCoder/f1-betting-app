"""Tests for the prediction models.

The concrete models (Elo, logistic, XGBoost, ensemble) are delivered in Phase 4.
This module currently verifies the abstract contract only; per-model tests are
added as each model lands.
"""
from __future__ import annotations

import inspect

from models.base_model import BaseModel


def test_base_model_is_abstract():
    """BaseModel cannot be instantiated directly."""
    assert inspect.isabstract(BaseModel)


def test_base_model_defines_interface():
    """The required abstract methods are declared on the interface."""
    for method in ("name", "train", "predict", "evaluate"):
        assert hasattr(BaseModel, method)
