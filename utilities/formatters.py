"""Display formatting helpers.

Pure functions that turn raw numeric values into human-readable strings for the
UI and reports. Kept free of any UI-framework imports.
"""
from __future__ import annotations


def format_lap_time(time_ms: int | float | None) -> str:
    """Format a lap/sector time in milliseconds as ``M:SS.mmm``.

    Args:
        time_ms: Duration in milliseconds, or ``None``.

    Returns:
        A string like ``"1:23.456"``, or ``"—"`` when the input is ``None``.
    """
    if time_ms is None:
        return "—"
    total_seconds = time_ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds - minutes * 60
    return f"{minutes}:{seconds:06.3f}"


def format_odds(decimal_odds: float | None) -> str:
    """Format decimal odds to two decimal places.

    Args:
        decimal_odds: Decimal odds, or ``None``.

    Returns:
        A string like ``"3.50"``, or ``"—"`` when the input is ``None``.
    """
    if decimal_odds is None:
        return "—"
    return f"{decimal_odds:.2f}"


def format_percentage(value: float | None, decimals: int = 1) -> str:
    """Format a fractional value as a percentage string.

    Args:
        value: A fraction (0.412) to render as a percentage.
        decimals: Number of decimal places.

    Returns:
        A string like ``"41.2%"``, or ``"—"`` when the input is ``None``.
    """
    if value is None:
        return "—"
    return f"{value * 100:.{decimals}f}%"


def format_signed_percentage(value: float | None, decimals: int = 1) -> str:
    """Format a fractional value as a signed percentage (for edges/EV).

    Args:
        value: A fraction (0.102) to render as ``"+10.2%"``.
        decimals: Number of decimal places.

    Returns:
        A signed percentage string, or ``"—"`` when the input is ``None``.
    """
    if value is None:
        return "—"
    return f"{value * 100:+.{decimals}f}%"


def format_currency(amount: float | None, symbol: str = "£") -> str:
    """Format a monetary amount with a currency symbol and thousands separators.

    Args:
        amount: The amount, or ``None``.
        symbol: Currency symbol to prefix.

    Returns:
        A string like ``"£1,250.00"``, or ``"—"`` when the input is ``None``.
    """
    if amount is None:
        return "—"
    return f"{symbol}{amount:,.2f}"
