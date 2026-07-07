"""Expected-value calculations.

Pure functions relating a model's probability estimate to the price on offer.
"""
from __future__ import annotations


def calculate_ev(prob: float, decimal_odds: float) -> float:
    """Return expected value per unit staked.

    ``EV = prob * (decimal_odds - 1) - (1 - prob)`` which simplifies to
    ``prob * decimal_odds - 1``. A positive value indicates a +EV bet.

    Args:
        prob: Model probability of the outcome, in [0, 1].
        decimal_odds: Decimal odds offered, must be greater than 1.0.

    Returns:
        Expected profit per 1 unit staked.

    Raises:
        ValueError: If ``prob`` is outside [0, 1] or ``decimal_odds`` <= 1.0.
    """
    if not 0.0 <= prob <= 1.0:
        raise ValueError(f"Probability must be in [0, 1], got {prob}.")
    if decimal_odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {decimal_odds}.")
    return prob * decimal_odds - 1.0


def calculate_ev_percentage(prob: float, decimal_odds: float) -> float:
    """Return expected value as a percentage of stake.

    Args:
        prob: Model probability of the outcome, in [0, 1].
        decimal_odds: Decimal odds offered, must be greater than 1.0.

    Returns:
        Expected value expressed as a percentage (e.g. ``10.2`` for +10.2%).
    """
    return calculate_ev(prob, decimal_odds) * 100.0
