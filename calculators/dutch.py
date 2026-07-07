"""Dutch-betting calculations.

Pure functions. Dutching splits a stake across several selections so that the
return is identical whichever of them wins.
"""
from __future__ import annotations

from typing import List

from calculators.arbitrage import _validate_odds


def dutch_stakes(odds_list: List[float], total_stake: float) -> List[float]:
    """Split a total stake across selections for equal return.

    Args:
        odds_list: Decimal odds for each selection.
        total_stake: Total amount to distribute.

    Returns:
        Stakes (same order as ``odds_list``) yielding an equal payout for any
        winning selection.

    Raises:
        ValueError: If fewer than two odds are given or any is <= 1.0.
    """
    _validate_odds(odds_list)
    inverse_sum = sum(1.0 / o for o in odds_list)
    return [(total_stake / o) / inverse_sum for o in odds_list]


def dutch_profit(odds_list: List[float], total_stake: float) -> float:
    """Return the (constant) profit from a dutched book if a selection wins.

    Positive when the book is an arbitrage, negative when it carries overround.

    Args:
        odds_list: Decimal odds for each selection.
        total_stake: Total amount staked across selections.

    Returns:
        Profit = guaranteed_return - total_stake.
    """
    stakes = dutch_stakes(odds_list, total_stake)
    # Every selection returns the same amount by construction; use the first.
    guaranteed_return = stakes[0] * odds_list[0]
    return guaranteed_return - total_stake
