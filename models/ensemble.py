"""Model ensemble.

Combines several :class:`BaseModel` instances into a single weighted-average
win-probability model. Weights default to uniform and are re-normalised over the
models that are actually present.
"""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

import pandas as pd

from models._common import normalize_probabilities
from models.base_model import BaseModel
from models.elo_model import evaluate_win_predictions


class EnsembleModel(BaseModel):
    """Weighted average of member models' win probabilities."""

    def __init__(
        self,
        models: Sequence[BaseModel],
        weights: Mapping[str, float] | None = None,
    ) -> None:
        if not models:
            raise ValueError("EnsembleModel requires at least one member model.")
        self._models = list(models)
        self._weights = self._normalise_weights(weights)

    def _normalise_weights(self, weights: Mapping[str, float] | None) -> dict[str, float]:
        """Return per-model weights summing to 1 over the member models."""
        names = [m.name for m in self._models]
        raw = {n: (weights.get(n, 0.0) if weights else 1.0) for n in names}
        total = sum(raw.values())
        if total <= 0:  # fall back to uniform
            return {n: 1.0 / len(names) for n in names}
        return {n: w / total for n, w in raw.items()}

    @property
    def name(self) -> str:
        return "ensemble"

    @property
    def weights(self) -> dict[str, float]:
        """Return the effective per-model weights."""
        return dict(self._weights)

    def train(self, features: pd.DataFrame, target: pd.Series) -> None:
        """Train every member model on the same data."""
        for model in self._models:
            model.train(features, target)

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return the weighted-average win probabilities across member models."""
        combined: pd.DataFrame | None = None
        for model in self._models:
            preds = model.predict(features).set_index("driver_id")["probability"]
            contribution = preds * self._weights[model.name]
            combined = contribution if combined is None else combined.add(
                contribution, fill_value=0.0
            )
        out = combined.reset_index()
        out.columns = ["driver_id", "probability"]
        return normalize_probabilities(out)

    def predict_per_model(self, features: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Return each member model's individual prediction, keyed by name.

        Useful for the model-agreement component of the confidence score.
        """
        return {m.name: m.predict(features) for m in self._models}

    def evaluate(self, predictions: pd.DataFrame, actuals: pd.Series) -> Dict[str, float]:
        """Return log-loss, Brier score and accuracy."""
        return evaluate_win_predictions(predictions, actuals)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return the ensemble weights as the top-level importance view."""
        return dict(self._weights)
