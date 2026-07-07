"""Bankroll growth and risk-of-ruin calculations.

Pure functions used by the Playground bankroll simulator and dashboards.
"""
from __future__ import annotations

from typing import List


def growth_projection(
    bankroll: float,
    avg_ev: float,
    bets_per_race: int,
    races: int,
) -> List[float]:
    """Project bankroll growth over a season under a constant edge.

    Uses a simple compounding model: each race the bankroll grows by
    ``avg_ev * bets_per_race`` (EV expressed as a fraction of the amount at
    risk per bet, approximated as a fraction of bankroll).

    Args:
        bankroll: Starting bankroll, must be non-negative.
        avg_ev: Average expected value per bet as a fraction (0.05 == 5%).
        bets_per_race: Number of bets placed per race, must be non-negative.
        races: Number of races to project over, must be non-negative.

    Returns:
        A list of length ``races + 1`` giving the bankroll after each race,
        starting with the initial value.

    Raises:
        ValueError: If any argument is negative.
    """
    if bankroll < 0 or bets_per_race < 0 or races < 0:
        raise ValueError("Bankroll, bets_per_race and races must be non-negative.")
    growth_rate = avg_ev * bets_per_race
    trajectory = [bankroll]
    current = bankroll
    for _ in range(races):
        current *= 1.0 + growth_rate
        trajectory.append(current)
    return trajectory


def risk_of_ruin(
    bankroll: float,
    avg_stake: float,
    win_rate: float,
    avg_odds: float,
) -> float:
    """Estimate the probability of losing the entire bankroll.

    Uses the classic even-money gambler's-ruin approximation generalised for
    a per-bet edge. Returns 0.0 when the bettor holds a positive edge and the
    formula is stable; otherwise clamps to [0, 1].

    Args:
        bankroll: Current bankroll, must be positive.
        avg_stake: Average stake per bet, must be positive.
        win_rate: Probability of winning a single bet, in [0, 1].
        avg_odds: Average decimal odds, must be greater than 1.0.

    Returns:
        Estimated risk of ruin in [0, 1].

    Raises:
        ValueError: If inputs are out of range.
    """
    if bankroll <= 0 or avg_stake <= 0:
        raise ValueError("Bankroll and avg_stake must be positive.")
    if not 0.0 <= win_rate <= 1.0:
        raise ValueError(f"win_rate must be in [0, 1], got {win_rate}.")
    if avg_odds <= 1.0:
        raise ValueError(f"avg_odds must be > 1.0, got {avg_odds}.")

    b = avg_odds - 1.0  # net odds received on a win
    loss_rate = 1.0 - win_rate
    # Edge per unit staked; if non-positive, ruin is effectively certain.
    edge = win_rate * b - loss_rate
    if edge <= 0:
        return 1.0

    units = bankroll / avg_stake
    # Ratio of loss to (edge-adjusted) win expectation, per unit.
    ratio = loss_rate / (win_rate * b)
    ror = ratio**units
    return max(0.0, min(1.0, ror))
