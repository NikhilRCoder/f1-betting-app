"""Monte Carlo race simulator.

Simulates many races from per-driver strength estimates using a Plackett–Luce
sampling scheme (Gumbel-noise on log-strengths, then rank). Produces win/podium/
top-N market probabilities. Also usable as a :class:`BaseModel` for the win
market so it can be ensembled and backtested.
"""
from __future__ import annotations

from typing import Dict, Mapping

import numpy as np
import pandas as pd

from models._common import normalize_probabilities
from models.base_model import BaseModel
from models.elo_model import evaluate_win_predictions
from models.power_ratings import PowerRatingsModel

_MARKET_CUTOFFS = {"race_winner": 1, "podium": 3, "top5": 5, "top10": 10}


def simulate_markets(
    strengths: Mapping[int, float], n_sims: int = 10_000, seed: int | None = None
) -> dict[int, dict[str, float]]:
    """Simulate races and return per-driver market probabilities.

    Args:
        strengths: Mapping of ``driver_id`` to a positive strength score
            (higher = faster). Non-positive values are floored to a small ε.
        n_sims: Number of race simulations to run.
        seed: Optional RNG seed for reproducibility.

    Returns:
        Mapping of ``driver_id`` to a dict of market → probability for each of
        ``race_winner``, ``podium``, ``top5`` and ``top10``.
    """
    rng = np.random.default_rng(seed)
    drivers = list(strengths)
    if not drivers:
        return {}
    log_strength = np.log(np.array([max(strengths[d], 1e-6) for d in drivers]))

    # Plackett–Luce: add Gumbel noise to log-strengths and rank descending.
    gumbel = rng.gumbel(size=(n_sims, len(drivers)))
    scores = log_strength[None, :] + gumbel
    # Rank 0 = best (highest score) per simulation.
    ranks = (-scores).argsort(axis=1).argsort(axis=1)

    result: dict[int, dict[str, float]] = {}
    for idx, did in enumerate(drivers):
        driver_ranks = ranks[:, idx]
        result[did] = {
            market: float(np.mean(driver_ranks < cutoff))
            for market, cutoff in _MARKET_CUTOFFS.items()
        }
    return result


def head_to_head_prob(strengths: Mapping[int, float], a: int, b: int) -> float:
    """Return P(driver ``a`` finishes ahead of driver ``b``).

    Under the Plackett–Luce model this has the closed form
    ``s_a / (s_a + s_b)`` where ``s`` is each driver's strength (win
    probability). Deterministic — no simulation needed.

    Args:
        strengths: Mapping of driver id to a positive strength.
        a: The primary driver id.
        b: The comparison driver id.

    Returns:
        Probability in [0, 1] that ``a`` beats ``b``.

    Raises:
        KeyError: If either driver id is absent from ``strengths``.
    """
    sa = max(float(strengths[a]), 1e-9)
    sb = max(float(strengths[b]), 1e-9)
    return sa / (sa + sb)


class MonteCarloModel(BaseModel):
    """Monte Carlo win model driven by power-ratings strengths."""

    def __init__(self, n_sims: int = 10_000, seed: int | None = 42) -> None:
        self._power = PowerRatingsModel()
        self._n_sims = n_sims
        self._seed = seed

    @property
    def name(self) -> str:
        return "monte_carlo"

    def train(self, features: pd.DataFrame, target: pd.Series | None = None) -> None:
        """Calibrate the underlying power-ratings strength model."""
        self._power.train(features, target)

    def _strengths(self, features: pd.DataFrame) -> dict[int, float]:
        """Return positive strength scores per driver from power probabilities."""
        probs = self._power.predict(features)
        return {
            int(r["driver_id"]): max(float(r["probability"]), 1e-6)
            for _, r in probs.iterrows()
        }

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return simulated win probabilities for the race field."""
        markets = simulate_markets(self._strengths(features), self._n_sims, self._seed)
        out = pd.DataFrame(
            {
                "driver_id": list(markets),
                "probability": [markets[d]["race_winner"] for d in markets],
            }
        )
        return normalize_probabilities(out)

    def simulate(self, features: pd.DataFrame) -> dict[int, dict[str, float]]:
        """Return full multi-market simulation output for a race field."""
        return simulate_markets(self._strengths(features), self._n_sims, self._seed)

    def evaluate(self, predictions: pd.DataFrame, actuals: pd.Series) -> Dict[str, float]:
        """Return log-loss, Brier score and accuracy."""
        return evaluate_win_predictions(predictions, actuals)
