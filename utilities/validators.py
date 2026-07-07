"""Input validation helpers.

Pure predicate/guard functions used to validate user input before it reaches
services or the database.
"""
from __future__ import annotations

from config import settings


def is_valid_decimal_odds(odds: float) -> bool:
    """Return ``True`` if ``odds`` is valid decimal odds (> 1.0)."""
    return isinstance(odds, (int, float)) and odds > 1.0


def is_valid_probability(prob: float) -> bool:
    """Return ``True`` if ``prob`` is a probability in [0, 1]."""
    return isinstance(prob, (int, float)) and 0.0 <= prob <= 1.0


def is_valid_market(market: str) -> bool:
    """Return ``True`` if ``market`` is a recognised betting market."""
    return market in settings.MARKETS


def is_valid_verdict(verdict: str) -> bool:
    """Return ``True`` if ``verdict`` is a recognised recommendation verdict."""
    return verdict in settings.VERDICTS


def require(condition: bool, message: str) -> None:
    """Raise :class:`ValueError` with ``message`` if ``condition`` is falsy.

    A small guard helper to keep service-layer validation terse and readable.
    """
    if not condition:
        raise ValueError(message)
