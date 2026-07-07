"""Gradient-boosted win model (XGBoost).

Fits an ``XGBClassifier`` on the engineered feature matrix. The XGBoost import is
guarded so importing this module never fails; a clear error is raised at train
time if the dependency is missing.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from models._common import normalize_probabilities
from models.base_model import BaseModel
from models.elo_model import evaluate_win_predictions
from models.feature_engineering import FEATURE_COLUMNS

try:  # pragma: no cover - exercised implicitly by availability
    from xgboost import XGBClassifier

    _XGBOOST_AVAILABLE = True
except ImportError:  # pragma: no cover
    _XGBOOST_AVAILABLE = False


class XGBoostModel(BaseModel):
    """Gradient-boosted trees over engineered features."""

    def __init__(self, n_estimators: int = 150, max_depth: int = 4) -> None:
        self._model = None
        self._columns = list(FEATURE_COLUMNS)
        self._n_estimators = n_estimators
        self._max_depth = max_depth

    @property
    def name(self) -> str:
        return "xgboost"

    @staticmethod
    def is_available() -> bool:
        """Return ``True`` if XGBoost is installed."""
        return _XGBOOST_AVAILABLE

    def train(self, features: pd.DataFrame, target: pd.Series) -> None:
        """Fit the classifier on the feature matrix.

        Raises:
            RuntimeError: If XGBoost is not installed.
            ValueError: If the target has only one class.
        """
        if not _XGBOOST_AVAILABLE:
            raise RuntimeError(
                "xgboost is required for XGBoostModel. Install it via "
                "requirements.txt / environment.yml."
            )
        x = features[self._columns].astype(float).to_numpy()
        y = target.astype(int).to_numpy()
        if len(np.unique(y)) < 2:
            raise ValueError("Training target must contain both wins and non-wins.")
        # Class imbalance: winners are ~1/field_size of rows.
        positives = max(int(y.sum()), 1)
        scale_pos_weight = (len(y) - positives) / positives
        self._model = XGBClassifier(
            n_estimators=self._n_estimators,
            max_depth=self._max_depth,
            learning_rate=0.1,
            subsample=0.9,
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
        )
        self._model.fit(x, y)

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return per-driver win probabilities, normalised across the race."""
        if self._model is None:
            raise RuntimeError("XGBoostModel must be trained before predicting.")
        x = features[self._columns].astype(float).to_numpy()
        raw = self._model.predict_proba(x)[:, 1]
        out = pd.DataFrame(
            {"driver_id": features["driver_id"].tolist(), "probability": raw}
        )
        return normalize_probabilities(out)

    def evaluate(self, predictions: pd.DataFrame, actuals: pd.Series) -> Dict[str, float]:
        """Return log-loss, Brier score and accuracy."""
        return evaluate_win_predictions(predictions, actuals)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return XGBoost feature importances per feature."""
        if self._model is None:
            return {}
        importances = self._model.feature_importances_
        return {c: round(float(w), 4) for c, w in zip(self._columns, importances)}
