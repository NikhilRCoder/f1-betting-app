"""Miscellaneous shared utility functions.

Small, dependency-light helpers reused across layers.
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Sequence, TypeVar

T = TypeVar("T")


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide two numbers, returning ``default`` on division by zero."""
    return numerator / denominator if denominator else default


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive range ``[low, high]``."""
    return max(low, min(high, value))


def chunked(items: Sequence[T], size: int) -> Iterable[Sequence[T]]:
    """Yield successive ``size``-length chunks from ``items``."""
    if size <= 0:
        raise ValueError("Chunk size must be positive.")
    for start in range(0, len(items), size):
        yield items[start : start + size]


def to_json(obj: Any) -> str:
    """Serialise ``obj`` to a compact JSON string (for feature blobs etc.)."""
    return json.dumps(obj, separators=(",", ":"), default=str)


def from_json(text: str | None) -> Any:
    """Deserialise a JSON string, returning ``None`` for empty/invalid input."""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def rolling_average(values: Sequence[float], window: int) -> float | None:
    """Return the mean of the last ``window`` values, or ``None`` if empty.

    Uses up to ``window`` most-recent values; fewer are averaged if that many
    are not available.
    """
    if not values:
        return None
    recent = list(values)[-window:]
    return sum(recent) / len(recent)
