"""Custom power-ratings model.

A transparent, weighted-score rating: each driver's power score blends recent
form, career win rate and constructor reliability. Win probabilities are the
softmax of power scores over a race's field. Pure NumPy.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from models._common import normalize_probabilities, softmax
from models.base_model import BaseModel
from models.elo_model import evaluate_win_predictions

# Weights over engineered features (higher score = stronger).
_WEIGHTS = {
    "rolling_finish_5": -1.0,   # lower avg finish is better
    "career_win_rate": 40.0,
    "constructor_reliability": 5.0,
    "momentum": 3.0,
    "quali_pos": -0.8,
}


class PowerRatingsModel(BaseModel):
    """Weighted power-ratings model over engineered features."""

    def __init__(self, temperature: float = 4.0) -> None:
        self._temperature = temperature
        self._baseline = 0.0

    @property
    def name(self) -> str:
        return "power_ratings"

    def train(self, features: pd.DataFrame, target: pd.Series | None = None) -> None:
        """Calibrate the score baseline to the training data's mean score."""
        if features.empty:
            self._baseline = 0.0
            return
        self._baseline = float(self._score(features).mean())

    def _score(self, features: pd.DataFrame) -> pd.Series:
        """Return the raw weighted power score per row."""
        score = pd.Series(0.0, index=features.index)
        for col, weight in _WEIGHTS.items():
            if col in features:
                score = score + features[col].astype(float) * weight
        return score

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return normalised win probabilities via softmax of power scores."""
        scores = (self._score(features) - self._baseline).to_numpy(dtype=float)
        probs = softmax(scores, temperature=self._temperature)
        out = pd.DataFrame(
            {"driver_id": features["driver_id"].tolist(), "probability": probs}
        )
        return normalize_probabilities(out)

    def evaluate(self, predictions: pd.DataFrame, actuals: pd.Series) -> Dict[str, float]:
        """Return log-loss, Brier score and accuracy."""
        return evaluate_win_predictions(predictions, actuals)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return the fixed feature weights."""
        return dict(_WEIGHTS)
