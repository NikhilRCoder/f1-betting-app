"""Feature pipeline shared across models.

``FeatureEngineer`` builds a leak-free feature matrix from the database. Every
per-race feature is computed using only information available *before* that race
(prior results, that weekend's qualifying), so backtests and live predictions
use the same code path without look-ahead bias.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from database.connection import get_connection

# Columns the models train/predict on (ids, date and target are excluded).
FEATURE_COLUMNS: tuple[str, ...] = (
    "grid",
    "quali_pos",
    "rolling_finish_5",
    "career_win_rate",
    "dnf_rate",
    "constructor_reliability",
    "is_street",
    "is_permanent",
    "momentum",
)

TARGET_COLUMN: str = "won"

_BASE_QUERY = """
    SELECT
        res.race_id,
        res.driver_id,
        res.constructor_id,
        r.date              AS date,
        r.season            AS season,
        res.grid            AS grid,
        res.position        AS position,
        q.position          AS quali_pos,
        c.circuit_type      AS circuit_type
    FROM results res
    JOIN races r      ON r.id = res.race_id
    JOIN circuits c   ON c.id = r.circuit_id
    LEFT JOIN qualifying q
           ON q.race_id = res.race_id AND q.driver_id = res.driver_id
    ORDER BY r.date ASC, res.race_id ASC
"""


class FeatureEngineer:
    """Builds model-ready feature matrices from historical data."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path

    def _load_raw(self) -> pd.DataFrame:
        """Load the joined results/qualifying/circuit frame ordered by date."""
        with get_connection(self._db_path) as conn:
            rows = conn.execute(_BASE_QUERY).fetchall()
        return pd.DataFrame([dict(r) for r in rows])

    def build_matrix(self, seasons: Sequence[int] | None = None) -> pd.DataFrame:
        """Return the full leak-free feature matrix.

        Args:
            seasons: Optional subset of seasons to return rows for. Features are
                still computed from the complete prior history regardless.

        Returns:
            A DataFrame with :data:`FEATURE_COLUMNS`, id/date columns and the
            binary :data:`TARGET_COLUMN` (1 = race win).
        """
        raw = self._load_raw()
        if raw.empty:
            return pd.DataFrame(
                columns=[
                    "race_id", "driver_id", "constructor_id", "date", "season",
                    *FEATURE_COLUMNS, "finish_pos", TARGET_COLUMN,
                ]
            )

        raw = raw.sort_values(["date", "race_id"]).reset_index(drop=True)
        raw["finished"] = raw["position"].notna().astype(int)
        raw["is_win"] = (raw["position"] == 1).astype(int)
        raw["is_street"] = (raw["circuit_type"] == "street").astype(int)
        raw["is_permanent"] = (raw["circuit_type"] == "permanent").astype(int)

        # Per-driver, prior-only (shifted) rolling / expanding statistics.
        g = raw.groupby("driver_id", group_keys=False)
        raw["rolling_finish_5"] = g["position"].apply(
            lambda s: s.shift(1).rolling(5, min_periods=1).mean()
        )
        raw["career_win_rate"] = g["is_win"].apply(
            lambda s: s.shift(1).expanding().mean()
        )
        raw["dnf_rate"] = g["finished"].apply(
            lambda s: 1.0 - s.shift(1).expanding().mean()
        )
        raw["momentum"] = g["position"].apply(_prior_momentum)

        # Constructor reliability (prior finishes / prior entries), shifted.
        gc = raw.groupby("constructor_id", group_keys=False)
        raw["constructor_reliability"] = gc["finished"].apply(
            lambda s: s.shift(1).expanding().mean()
        )

        raw["quali_pos"] = raw["quali_pos"].fillna(raw["grid"])
        raw["grid"] = raw["grid"].fillna(raw["quali_pos"])
        raw[TARGET_COLUMN] = raw["is_win"]
        # Actual finishing position of this race. Not a feature (excluded from
        # FEATURE_COLUMNS) — used by rating models during training and as the
        # ground-truth for evaluation. No leakage into the ML feature set.
        raw["finish_pos"] = raw["position"]

        matrix = raw[
            [
                "race_id", "driver_id", "constructor_id", "date", "season",
                *FEATURE_COLUMNS, "finish_pos", TARGET_COLUMN,
            ]
        ].copy()
        matrix = self._fill_defaults(matrix)

        if seasons is not None:
            matrix = matrix[matrix["season"].isin(list(seasons))]
        return matrix.reset_index(drop=True)

    def build_race_features(self, race_id: int) -> pd.DataFrame:
        """Return the feature rows for a single (already-run) race.

        Features reflect the state *before* the race, so this is suitable for
        backtesting a model's prediction of that race.
        """
        matrix = self.build_matrix()
        return matrix[matrix["race_id"] == race_id].reset_index(drop=True)

    @staticmethod
    def _fill_defaults(matrix: pd.DataFrame) -> pd.DataFrame:
        """Fill first-appearance NaNs with neutral defaults."""
        defaults = {
            "grid": 11.0,
            "quali_pos": 11.0,
            "rolling_finish_5": 11.0,
            "career_win_rate": 0.0,
            "dnf_rate": 0.15,
            "constructor_reliability": 0.85,
            "momentum": 0.0,
            "is_street": 0,
            "is_permanent": 0,
        }
        for col, value in defaults.items():
            matrix[col] = matrix[col].fillna(value)
        return matrix


def _prior_momentum(series: pd.Series) -> pd.Series:
    """Rolling momentum from the previous up-to-5 finishing positions.

    Positive means improving (finishing positions trending toward P1). Computed
    per row from the prior window only, so it is leak-free.
    """
    shifted = series.shift(1)
    out = []
    history: list[float] = []
    for value in shifted:
        window = [v for v in history[-5:] if not pd.isna(v)]
        if len(window) >= 2:
            xs = np.arange(len(window))
            slope = np.polyfit(xs, window, 1)[0]
            out.append(-slope)
        else:
            out.append(0.0)
        history.append(value)
    return pd.Series(out, index=series.index)
