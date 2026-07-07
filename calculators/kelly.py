"""Kelly-criterion stake sizing.

Pure functions. The Kelly fraction maximises the long-run growth rate of a
bankroll. Fractional Kelly scales that down to reduce variance.
"""
from __future__ import annotations


def full_kelly(prob: float, decimal_odds: float) -> float:
    """Return the full-Kelly fraction of bankroll to stake.

    ``f* = (b * p - q) / b`` where ``b = decimal_odds - 1``, ``p = prob`` and
    ``q = 1 - prob``. Negative results (no edge) are clamped to 0.

    Args:
        prob: Win probability, in [0, 1].
        decimal_odds: Decimal odds offered, must be greater than 1.0.

    Returns:
        Fraction of bankroll in [0, 1] to stake (0 when there is no edge).

    Raises:
        ValueError: If ``prob`` is outside [0, 1] or ``decimal_odds`` <= 1.0.
    """
    if not 0.0 <= prob <= 1.0:
        raise ValueError(f"Probability must be in [0, 1], got {prob}.")
    if decimal_odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {decimal_odds}.")
    b = decimal_odds - 1.0
    q = 1.0 - prob
    fraction = (b * prob - q) / b
    return max(0.0, fraction)


def fractional_kelly(
    prob: float, decimal_odds: float, fraction: float = 0.25
) -> float:
    """Return a scaled-down Kelly fraction.

    Args:
        prob: Win probability, in [0, 1].
        decimal_odds: Decimal odds offered, must be greater than 1.0.
        fraction: Kelly multiplier (e.g. 0.25 for quarter-Kelly).

    Returns:
        The full-Kelly fraction multiplied by ``fraction``.
    """
    return full_kelly(prob, decimal_odds) * fraction


def kelly_stake(
    bankroll: float,
    prob: float,
    decimal_odds: float,
    fraction: float = 0.25,
) -> float:
    """Return the monetary stake implied by fractional Kelly.

    Args:
        bankroll: Current bankroll in currency units, must be non-negative.
        prob: Win probability, in [0, 1].
        decimal_odds: Decimal odds offered, must be greater than 1.0.
        fraction: Kelly multiplier.

    Returns:
        The recommended stake in the same units as ``bankroll``.

    Raises:
        ValueError: If ``bankroll`` is negative.
    """
    if bankroll < 0:
        raise ValueError(f"Bankroll must be non-negative, got {bankroll}.")
    return bankroll * fractional_kelly(prob, decimal_odds, fraction)
