"""ROI, yield and closing-line-value calculations.

Pure functions for measuring realised betting performance.
"""
from __future__ import annotations


def calculate_roi(total_profit: float, total_staked: float) -> float:
    """Return return-on-investment as a percentage.

    Args:
        total_profit: Net profit (payouts minus stakes).
        total_staked: Total amount staked. Returns 0.0 if this is 0.

    Returns:
        ROI as a percentage (``profit / staked * 100``).
    """
    if total_staked == 0:
        return 0.0
    return total_profit / total_staked * 100.0


def calculate_yield(total_profit: float, num_bets: int) -> float:
    """Return average profit per bet.

    Args:
        total_profit: Net profit across all bets.
        num_bets: Number of bets placed. Returns 0.0 if this is 0.

    Returns:
        Average profit per bet.
    """
    if num_bets == 0:
        return 0.0
    return total_profit / num_bets


def closing_line_value(odds_taken: float, closing_odds: float) -> float:
    """Return closing-line value as a percentage.

    Beating the closing line is the strongest predictor of long-term edge.
    ``CLV = (odds_taken / closing_odds - 1) * 100``.

    Args:
        odds_taken: Decimal odds obtained when the bet was placed, > 1.0.
        closing_odds: Decimal odds at market close, > 1.0.

    Returns:
        CLV as a percentage; positive means the bet beat the close.

    Raises:
        ValueError: If either odds value is not greater than 1.0.
    """
    if odds_taken <= 1.0 or closing_odds <= 1.0:
        raise ValueError("Both odds values must be > 1.0.")
    return (odds_taken / closing_odds - 1.0) * 100.0
