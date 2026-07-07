"""Logistic-regression win model (scikit-learn).

Fits a logistic regression on the engineered feature matrix to predict the
probability that a driver wins, then normalises probabilities across each race.
The scikit-learn import is guarded so importing this module never fails; a clear
error is raised at train time if the dependency is missing.
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
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SKLEARN_AVAILABLE = False


class LogisticModel(BaseModel):
    """Logistic-regression classifier over engineered features."""

    def __init__(self) -> None:
        self._model = None
        self._scaler = None
        self._columns = list(FEATURE_COLUMNS)

    @property
    def name(self) -> str:
        return "logistic"

    @staticmethod
    def is_available() -> bool:
        """Return ``True`` if scikit-learn is installed."""
        return _SKLEARN_AVAILABLE

    def train(self, features: pd.DataFrame, target: pd.Series) -> None:
        """Fit the scaler and logistic regression on the feature matrix.

        Raises:
            RuntimeError: If scikit-learn is not installed.
            ValueError: If the target has only one class.
        """
        if not _SKLEARN_AVAILABLE:
            raise RuntimeError(
                "scikit-learn is required for LogisticModel. Install it via "
                "requirements.txt / environment.yml."
            )
        x = features[self._columns].astype(float).to_numpy()
        y = target.astype(int).to_numpy()
        if len(np.unique(y)) < 2:
            raise ValueError("Training target must contain both wins and non-wins.")
        self._scaler = StandardScaler().fit(x)
        self._model = LogisticRegression(max_iter=1000, class_weight="balanced")
        self._model.fit(self._scaler.transform(x), y)

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return per-driver win probabilities, normalised across the race."""
        if self._model is None or self._scaler is None:
            raise RuntimeError("LogisticModel must be trained before predicting.")
        x = self._scaler.transform(features[self._columns].astype(float).to_numpy())
        raw = self._model.predict_proba(x)[:, 1]
        out = pd.DataFrame(
            {"driver_id": features["driver_id"].tolist(), "probability": raw}
        )
        return normalize_probabilities(out)

    def evaluate(self, predictions: pd.DataFrame, actuals: pd.Series) -> Dict[str, float]:
        """Return log-loss, Brier score and accuracy."""
        return evaluate_win_predictions(predictions, actuals)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return absolute logistic coefficients per feature."""
        if self._model is None:
            return {}
        coefs = self._model.coef_[0]
        return {c: round(float(abs(w)), 4) for c, w in zip(self._columns, coefs)}
