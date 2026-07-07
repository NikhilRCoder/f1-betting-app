"""Arbitrage detection and stake allocation.

Pure functions. An arbitrage exists across mutually-exclusive, collectively-
exhaustive outcomes when the sum of implied probabilities is below 1.0.
"""
from __future__ import annotations

from typing import List, Tuple


def _validate_odds(odds_list: List[float]) -> None:
    """Validate a list of decimal odds for arbitrage/dutching maths."""
    if len(odds_list) < 2:
        raise ValueError("At least two outcomes are required.")
    if any(o <= 1.0 for o in odds_list):
        raise ValueError("All decimal odds must be > 1.0.")


def detect_arb(odds_list: List[float]) -> Tuple[bool, float]:
    """Detect whether a set of decimal odds forms an arbitrage.

    Args:
        odds_list: Decimal odds for each mutually-exclusive outcome.

    Returns:
        A tuple ``(is_arb, margin)`` where ``margin`` is
        ``1 - sum(1/odds)`` — the guaranteed profit fraction when positive.

    Raises:
        ValueError: If fewer than two odds are given or any is <= 1.0.
    """
    _validate_odds(odds_list)
    inverse_sum = sum(1.0 / o for o in odds_list)
    margin = 1.0 - inverse_sum
    return margin > 0.0, margin


def arb_stakes(odds_list: List[float], total_stake: float) -> List[float]:
    """Allocate a total stake across outcomes for an equal-return arbitrage.

    Args:
        odds_list: Decimal odds for each mutually-exclusive outcome.
        total_stake: Total amount to distribute across outcomes.

    Returns:
        A list of stakes (same order as ``odds_list``) that returns an equal
        payout regardless of which outcome wins.

    Raises:
        ValueError: If fewer than two odds are given or any is <= 1.0.
    """
    _validate_odds(odds_list)
    inverse_sum = sum(1.0 / o for o in odds_list)
    return [(total_stake / o) / inverse_sum for o in odds_list]
