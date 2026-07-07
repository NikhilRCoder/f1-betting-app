"""Odds and probability conversions.

Pure functions: no side effects, no I/O. Handles the three common odds formats
(decimal, fractional, American) and their relationship to implied probability.

Decimal odds are the canonical internal representation throughout PitWall.
"""
from __future__ import annotations

from math import gcd
from typing import Any


def decimal_to_implied(odds: float) -> float:
    """Convert decimal odds to implied probability.

    Args:
        odds: Decimal odds, must be greater than 1.0.

    Returns:
        Implied probability in the range (0, 1).

    Raises:
        ValueError: If ``odds`` is not greater than 1.0.
    """
    if odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {odds}.")
    return 1.0 / odds


def implied_to_decimal(prob: float) -> float:
    """Convert an implied probability to fair decimal odds.

    Args:
        prob: Probability in the open interval (0, 1).

    Returns:
        Fair decimal odds (``1 / prob``).

    Raises:
        ValueError: If ``prob`` is not within (0, 1).
    """
    if not 0.0 < prob < 1.0:
        raise ValueError(f"Probability must be in (0, 1), got {prob}.")
    return 1.0 / prob


def american_to_decimal(odds: int) -> float:
    """Convert American (moneyline) odds to decimal odds.

    Args:
        odds: American odds — positive for underdogs, negative for favourites.
            Zero is invalid.

    Returns:
        Equivalent decimal odds.

    Raises:
        ValueError: If ``odds`` is zero.
    """
    if odds == 0:
        raise ValueError("American odds cannot be zero.")
    if odds > 0:
        return 1.0 + odds / 100.0
    return 1.0 + 100.0 / abs(odds)


def decimal_to_american(odds: float) -> str:
    """Convert decimal odds to an American-odds string.

    Args:
        odds: Decimal odds, must be greater than 1.0.

    Returns:
        A signed string such as ``"+150"`` or ``"-200"``.

    Raises:
        ValueError: If ``odds`` is not greater than 1.0.
    """
    if odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {odds}.")
    if odds >= 2.0:
        american = round((odds - 1.0) * 100.0)
        return f"+{american}"
    american = round(-100.0 / (odds - 1.0))
    return str(american)


def fractional_to_decimal(num: int, den: int) -> float:
    """Convert fractional odds (num/den) to decimal odds.

    Args:
        num: Numerator (profit units).
        den: Denominator (stake units), must be non-zero.

    Returns:
        Equivalent decimal odds (``num/den + 1``).

    Raises:
        ValueError: If ``den`` is zero.
    """
    if den == 0:
        raise ValueError("Fractional denominator cannot be zero.")
    return num / den + 1.0


def decimal_to_fractional(odds: float) -> str:
    """Convert decimal odds to a simplified fractional-odds string.

    Args:
        odds: Decimal odds, must be greater than 1.0.

    Returns:
        A reduced fraction string such as ``"5/2"``.

    Raises:
        ValueError: If ``odds`` is not greater than 1.0.
    """
    if odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {odds}.")
    # Represent the profit fraction with a denominator of 100 then reduce.
    num = round((odds - 1.0) * 100)
    den = 100
    divisor = gcd(num, den) or 1
    return f"{num // divisor}/{den // divisor}"


def convert_all(odds: float, fmt: str) -> dict[str, Any]:
    """Convert odds in any supported format to every representation.

    Args:
        odds: The odds value. For ``"american"`` this is coerced to ``int``.
        fmt: One of ``"decimal"``, ``"american"``. For fractional input use
            :func:`fractional_to_decimal` first.

    Returns:
        A dict with ``decimal``, ``fractional``, ``american`` and
        ``implied_probability`` keys.

    Raises:
        ValueError: If ``fmt`` is not a recognised format.
    """
    fmt = fmt.lower()
    if fmt == "decimal":
        decimal = float(odds)
    elif fmt == "american":
        decimal = american_to_decimal(int(odds))
    else:
        raise ValueError(
            f"Unsupported format '{fmt}'. Use 'decimal' or 'american'."
        )
    return {
        "decimal": round(decimal, 4),
        "fractional": decimal_to_fractional(decimal),
        "american": decimal_to_american(decimal),
        "implied_probability": round(decimal_to_implied(decimal), 6),
    }
