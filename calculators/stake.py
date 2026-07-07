"""Stake-sizing helpers.

Pure functions for translating a chosen staking strategy into a monetary stake.
Kelly-based sizing lives in :mod:`calculators.kelly`; this module covers the
flat and percentage strategies plus a unified dispatcher.
"""
from __future__ import annotations

from calculators.kelly import kelly_stake


def flat_stake(unit: float) -> float:
    """Return a fixed flat stake.

    Args:
        unit: The flat unit size, must be non-negative.

    Returns:
        ``unit`` unchanged.

    Raises:
        ValueError: If ``unit`` is negative.
    """
    if unit < 0:
        raise ValueError(f"Unit must be non-negative, got {unit}.")
    return unit


def percentage_stake(bankroll: float, pct: float) -> float:
    """Return a stake as a percentage of bankroll.

    Args:
        bankroll: Current bankroll, must be non-negative.
        pct: Percentage of bankroll to stake (e.g. ``2.0`` for 2%).

    Returns:
        ``bankroll * pct / 100``.

    Raises:
        ValueError: If ``bankroll`` or ``pct`` is negative.
    """
    if bankroll < 0 or pct < 0:
        raise ValueError("Bankroll and pct must be non-negative.")
    return bankroll * pct / 100.0


def size_stake(
    strategy: str,
    bankroll: float,
    *,
    unit: float = 0.0,
    pct: float = 0.0,
    prob: float = 0.0,
    decimal_odds: float = 0.0,
    kelly_fraction: float = 0.25,
) -> float:
    """Dispatch to a staking strategy and return the monetary stake.

    Args:
        strategy: One of ``"flat"``, ``"percentage"`` or ``"kelly"``.
        bankroll: Current bankroll.
        unit: Flat unit size (used by the ``"flat"`` strategy).
        pct: Percentage of bankroll (used by the ``"percentage"`` strategy).
        prob: Win probability (used by the ``"kelly"`` strategy).
        decimal_odds: Decimal odds (used by the ``"kelly"`` strategy).
        kelly_fraction: Kelly multiplier (used by the ``"kelly"`` strategy).

    Returns:
        The recommended stake in bankroll units.

    Raises:
        ValueError: If ``strategy`` is unrecognised.
    """
    strategy = strategy.lower()
    if strategy == "flat":
        return flat_stake(unit)
    if strategy == "percentage":
        return percentage_stake(bankroll, pct)
    if strategy == "kelly":
        return kelly_stake(bankroll, prob, decimal_odds, kelly_fraction)
    raise ValueError(
        f"Unknown strategy '{strategy}'. Use 'flat', 'percentage' or 'kelly'."
    )
