"""Market overround (vig) calculations.

Pure functions. The overround is the bookmaker's built-in margin: the amount by
which summed implied probabilities exceed 1.0.
"""
from __future__ import annotations

from typing import List

from calculators.arbitrage import _validate_odds


def calculate_overround(odds_list: List[float]) -> float:
    """Return the market overround as a fraction.

    ``overround = sum(1/odds) - 1``. A value of ``0.05`` means a 5% margin.

    Args:
        odds_list: Decimal odds for every outcome in the market.

    Returns:
        The overround fraction (can be negative for an arbitrage market).

    Raises:
        ValueError: If fewer than two odds are given or any is <= 1.0.
    """
    _validate_odds(odds_list)
    return sum(1.0 / o for o in odds_list) - 1.0


def true_probabilities(odds_list: List[float]) -> List[float]:
    """Return margin-free ("true") probabilities via proportional normalisation.

    Each implied probability is divided by the summed implied probability so the
    result sums to exactly 1.0.

    Args:
        odds_list: Decimal odds for every outcome in the market.

    Returns:
        Normalised probabilities in the same order as ``odds_list``.

    Raises:
        ValueError: If fewer than two odds are given or any is <= 1.0.
    """
    _validate_odds(odds_list)
    implied = [1.0 / o for o in odds_list]
    total = sum(implied)
    return [p / total for p in implied]
