"""Elo rating model.

Maintains a per-driver Elo rating updated race-by-race from finishing order.
Win probabilities for a race are the softmax of the drivers' current ratings.
Pure NumPy — no heavy ML dependencies.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from models._common import normalize_probabilities, softmax
from models.base_model import BaseModel

_DEFAULT_RATING = 1500.0
_K_FACTOR = 24.0
_SCALE = 400.0


class EloModel(BaseModel):
    """Elo rating system adapted to multi-driver race outcomes."""

    def __init__(self, k_factor: float = _K_FACTOR, temperature: float = 200.0) -> None:
        self._k = k_factor
        self._temperature = temperature
        self._ratings: dict[int, float] = {}

    @property
    def name(self) -> str:
        return "elo"

    def train(self, features: pd.DataFrame, target: pd.Series | None = None) -> None:
        """Update ratings by replaying races in chronological order.

        Args:
            features: Matrix with ``race_id``, ``driver_id``, ``date`` and
                ``finish_pos`` columns (as produced by ``FeatureEngineer``).
            target: Unused; ratings are learned from finishing order.
        """
        self._ratings = {}
        if features.empty:
            return
        ordered = features.sort_values(["date", "race_id"])
        for _, race in ordered.groupby("race_id", sort=False):
            self._update_race(race)

    def _update_race(self, race: pd.DataFrame) -> None:
        """Apply pairwise Elo updates for a single race's classified finishers."""
        classified = race[race["finish_pos"].notna()]
        drivers = classified["driver_id"].tolist()
        positions = classified["finish_pos"].tolist()
        for did in drivers:
            self._ratings.setdefault(did, _DEFAULT_RATING)

        deltas: dict[int, float] = {d: 0.0 for d in drivers}
        for i in range(len(drivers)):
            for j in range(i + 1, len(drivers)):
                a, b = drivers[i], drivers[j]
                # Lower finishing position == better == "win".
                score_a = 1.0 if positions[i] < positions[j] else 0.0
                expected_a = 1.0 / (
                    1.0 + 10 ** ((self._ratings[b] - self._ratings[a]) / _SCALE)
                )
                change = self._k * (score_a - expected_a)
                deltas[a] += change
                deltas[b] -= change
        # Average the pairwise deltas so large fields don't inflate updates.
        divisor = max(len(drivers) - 1, 1)
        for d in drivers:
            self._ratings[d] += deltas[d] / divisor

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return win probabilities for the drivers in ``features``.

        Args:
            features: Frame containing a ``driver_id`` column.

        Returns:
            DataFrame with ``driver_id`` and normalised ``probability``.
        """
        drivers = features["driver_id"].tolist()
        ratings = np.array(
            [self._ratings.get(d, _DEFAULT_RATING) for d in drivers], dtype=float
        )
        probs = softmax(ratings, temperature=self._temperature)
        out = pd.DataFrame({"driver_id": drivers, "probability": probs})
        return normalize_probabilities(out)

    def evaluate(self, predictions: pd.DataFrame, actuals: pd.Series) -> Dict[str, float]:
        """Return log-loss, Brier score and top-1 accuracy."""
        return evaluate_win_predictions(predictions, actuals)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return current ratings as a driver_id → rating mapping."""
        return {str(k): round(v, 1) for k, v in sorted(self._ratings.items())}

    @property
    def ratings(self) -> dict[int, float]:
        """Expose the learned ratings (read-only view)."""
        return dict(self._ratings)


def evaluate_win_predictions(
    predictions: pd.DataFrame, actuals: pd.Series
) -> Dict[str, float]:
    """Compute standard classification metrics for win predictions.

    Args:
        predictions: DataFrame with a ``probability`` column aligned to
            ``actuals``.
        actuals: Binary win indicator (1 = won).

    Returns:
        ``{"log_loss", "brier_score", "accuracy"}``.
    """
    p = np.clip(predictions["probability"].to_numpy(dtype=float), 1e-9, 1 - 1e-9)
    y = actuals.to_numpy(dtype=float)
    log_loss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    brier = float(np.mean((p - y) ** 2))
    accuracy = float(np.mean((p >= 0.5) == (y >= 0.5)))
    return {
        "log_loss": round(log_loss, 4),
        "brier_score": round(brier, 4),
        "accuracy": round(accuracy, 4),
    }
