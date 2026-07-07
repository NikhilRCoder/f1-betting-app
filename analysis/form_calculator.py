"""Rolling form, momentum and streak calculations.

Pure functions operating on sequences of finishing positions (ordered oldest →
newest). ``None`` represents a DNF/DNS/DSQ (no classified position). No database
access — callers pass in the raw sequences, keeping this module fully testable.
"""
from __future__ import annotations

from typing import Sequence


def _classified(positions: Sequence[int | None]) -> list[int]:
    """Return only the classified (non-``None``) finishing positions."""
    return [p for p in positions if p is not None]


def rolling_average(positions: Sequence[int | None], window: int) -> float | None:
    """Return the mean classified finishing position over the last ``window`` races.

    DNFs (``None``) are ignored. Uses however many classified results fall inside
    the window; returns ``None`` if there are none.

    Args:
        positions: Finishing positions ordered oldest → newest.
        window: Number of most-recent races to consider.

    Returns:
        Mean finishing position, or ``None`` when no classified result exists.

    Raises:
        ValueError: If ``window`` is not positive.
    """
    if window <= 0:
        raise ValueError("window must be positive.")
    recent = _classified(list(positions)[-window:])
    if not recent:
        return None
    return sum(recent) / len(recent)


def momentum(positions: Sequence[int | None]) -> float:
    """Return a momentum score; positive means improving (moving toward P1).

    Computed as the least-squares slope of classified positions over their race
    index, negated so that a downward trend in position number (getting better)
    yields a positive momentum. Returns 0.0 when fewer than two classified
    results are available.

    Args:
        positions: Finishing positions ordered oldest → newest.

    Returns:
        Momentum score (positions gained per race, sign-flipped).
    """
    classified = _classified(positions)
    n = len(classified)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(classified) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, classified)) / denom
    return -slope


def streak(flags: Sequence[bool]) -> int:
    """Return the length of the current run of ``True`` values from the end.

    Args:
        flags: Booleans ordered oldest → newest (e.g. "finished in points").

    Returns:
        Count of consecutive trailing ``True`` values (0 if the last is False).
    """
    count = 0
    for flag in reversed(flags):
        if not flag:
            break
        count += 1
    return count


def form_score(
    positions: Sequence[int | None], window: int = 5, field_size: int = 20
) -> float:
    """Return a 0-100 form score from recent finishing positions.

    P1 maps to 100 and last place to ~0. DNFs count as last place, penalising
    unreliability. Returns 0.0 when there are no results in the window.

    Args:
        positions: Finishing positions ordered oldest → newest.
        window: Number of most-recent races to score over.
        field_size: Grid size used to normalise positions.

    Returns:
        Form score in [0, 100].

    Raises:
        ValueError: If ``window`` or ``field_size`` is not positive.
    """
    if window <= 0 or field_size <= 0:
        raise ValueError("window and field_size must be positive.")
    recent = list(positions)[-window:]
    if not recent:
        return 0.0
    scores = []
    for pos in recent:
        effective = field_size if pos is None else min(pos, field_size)
        scores.append((field_size - effective) / (field_size - 1) * 100.0)
    return sum(scores) / len(scores)


def dnf_rate(positions: Sequence[int | None]) -> float:
    """Return the fraction of races that ended without a classified position.

    Args:
        positions: Finishing positions ordered oldest → newest.

    Returns:
        DNF rate in [0, 1]; 0.0 for an empty sequence.
    """
    positions = list(positions)
    if not positions:
        return 0.0
    dnfs = sum(1 for p in positions if p is None)
    return dnfs / len(positions)
