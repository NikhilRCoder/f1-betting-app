"""Bayesian win model.

A Beta–Binomial shrinkage estimator: each driver's career win rate is shrunk
toward the field prior using pseudo-counts, then the posterior means are turned
into a race-winner distribution via normalisation. Pure NumPy.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

from models._common import normalize_probabilities
from models.base_model import BaseModel
from models.elo_model import evaluate_win_predictions

# Prior strength (pseudo-races) pulling sparse drivers toward the field mean.
_PRIOR_STRENGTH = 20.0


class BayesianModel(BaseModel):
    """Beta–Binomial shrinkage model over career win rate."""

    def __init__(self, prior_strength: float = _PRIOR_STRENGTH) -> None:
        self._prior_strength = prior_strength
        self._prior_mean = 0.05  # ~1/field_size baseline win rate

    @property
    def name(self) -> str:
        return "bayesian"

    def train(self, features: pd.DataFrame, target: pd.Series | None = None) -> None:
        """Estimate the field-wide prior win rate from the training target."""
        if target is not None and len(target):
            self._prior_mean = max(float(target.astype(float).mean()), 1e-3)

    def _posterior(self, features: pd.DataFrame) -> pd.Series:
        """Return the shrunk posterior win rate per row.

        ``career_win_rate`` is the observed rate; it is combined with the prior
        via pseudo-counts. Recent form (``rolling_finish_5``) nudges the estimate
        so in-form drivers are not purely history-bound.
        """
        alpha = self._prior_mean * self._prior_strength
        beta = (1.0 - self._prior_mean) * self._prior_strength
        observed = features.get("career_win_rate", pd.Series(0.0, index=features.index))
        # Treat the observed rate as if seen over a modest effective sample.
        effective_n = 15.0
        wins = observed.astype(float) * effective_n
        posterior = (alpha + wins) / (alpha + beta + effective_n)
        # Form adjustment: better recent finishes lift the estimate slightly.
        if "rolling_finish_5" in features:
            form_factor = (11.0 - features["rolling_finish_5"].astype(float)) / 100.0
            posterior = posterior * (1.0 + form_factor.clip(-0.1, 0.1))
        return posterior.clip(lower=1e-6)

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return normalised win probabilities from posterior win rates."""
        posterior = self._posterior(features)
        out = pd.DataFrame(
            {"driver_id": features["driver_id"].tolist(), "probability": posterior.to_numpy()}
        )
        return normalize_probabilities(out)

    def evaluate(self, predictions: pd.DataFrame, actuals: pd.Series) -> Dict[str, float]:
        """Return log-loss, Brier score and accuracy."""
        return evaluate_win_predictions(predictions, actuals)
