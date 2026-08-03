"""Probability calibration.

Model outputs are *relative* strengths turned into probabilities; they are not
guaranteed to match observed frequencies. A calibrator learns a monotonic map
from predicted probability to empirical win rate (isotonic regression) using
out-of-sample backtest pairs, so downstream expected-value and edge figures are
trustworthy.

The fitted map is stored as ``(x, y)`` threshold points and applied with linear
interpolation — no pickle, so it survives library upgrades.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np

_EPS = 1e-6


class ProbabilityCalibrator:
    """Monotonic (isotonic) probability calibrator."""

    def __init__(self) -> None:
        self._xs: np.ndarray | None = None
        self._ys: np.ndarray | None = None

    @property
    def fitted(self) -> bool:
        """Return ``True`` once the calibrator has been fit."""
        return self._xs is not None and self._ys is not None

    def fit(self, probs: Sequence[float], outcomes: Sequence[float]) -> "ProbabilityCalibrator":
        """Fit an isotonic map from predicted probability to observed frequency.

        Args:
            probs: Predicted probabilities.
            outcomes: Binary outcomes (1 = event occurred) aligned to ``probs``.

        Returns:
            ``self`` (fitted), or unfitted if there is too little/degenerate data.
        """
        from sklearn.isotonic import IsotonicRegression

        p = np.asarray(probs, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        if len(p) < 10 or len(np.unique(y)) < 2:
            # Not enough signal to calibrate; leave unfitted (identity).
            return self
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(p, y)
        self._xs = np.asarray(iso.X_thresholds_, dtype=float)
        self._ys = np.asarray(iso.y_thresholds_, dtype=float)
        return self

    def transform(self, probs: Sequence[float]) -> np.ndarray:
        """Apply the calibration map. Identity when unfitted.

        Args:
            probs: Predicted probabilities to calibrate.

        Returns:
            Calibrated probabilities, clipped to ``(0, 1)``.
        """
        p = np.asarray(probs, dtype=float)
        if not self.fitted:
            return np.clip(p, _EPS, 1 - _EPS)
        mapped = np.interp(p, self._xs, self._ys)
        return np.clip(mapped, _EPS, 1 - _EPS)

    # ── Persistence ──────────────────────────────────────────────────
    def save(self, path: Path) -> None:
        """Persist the calibration points to ``path`` as JSON."""
        if not self.fitted:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"xs": self._xs.tolist(), "ys": self._ys.tolist()}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "ProbabilityCalibrator":
        """Load a calibrator from ``path``; returns an unfitted one if absent."""
        cal = cls()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            cal._xs = np.asarray(data["xs"], dtype=float)
            cal._ys = np.asarray(data["ys"], dtype=float)
        return cal
