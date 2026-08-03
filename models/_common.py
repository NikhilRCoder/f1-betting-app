"""Shared helpers for prediction models.

Small, dependency-light utilities reused across model implementations. Prefixed
with an underscore so it is not mistaken for a concrete model module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_probabilities(df: pd.DataFrame, column: str = "probability") -> pd.DataFrame:
    """Return ``df`` with ``column`` scaled so it sums to 1 across the frame.

    Used to turn per-driver raw scores into a coherent race-winner distribution.
    If the column sums to zero, a uniform distribution is assigned instead.

    Args:
        df: A DataFrame containing ``driver_id`` and ``column``.
        column: The probability column to normalise.

    Returns:
        A copy of ``df`` with the normalised column.
    """
    out = df.copy()
    total = out[column].sum()
    if total <= 0:
        out[column] = 1.0 / len(out) if len(out) else 0.0
    else:
        out[column] = out[column] / total
    return out


def softmax(values: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Return the softmax of ``values`` with an optional temperature.

    Args:
        values: 1-D array of scores.
        temperature: Higher values flatten the distribution; must be > 0.

    Returns:
        A probability array summing to 1.
    """
    if temperature <= 0:
        raise ValueError("temperature must be positive.")
    shifted = (values - np.max(values)) / temperature
    exp = np.exp(shifted)
    return exp / exp.sum()
