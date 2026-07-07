"""Circuit analytical computations.

``CircuitAnalyzer`` profiles a circuit: race characteristics, grid importance and
the most successful drivers/constructors there.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from database.repositories.results import ResultRepository


class CircuitAnalyzer:
    """Compute circuit statistics from historical races and results."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._results = ResultRepository(db_path=db_path)
        self._db_path = db_path

    def race_characteristics(self, circuit_id: int) -> dict[str, Any]:
        """Return average safety cars, DNFs and race count at the circuit."""
        races = self._results.query(
            """
            SELECT id, safety_cars, virtual_safety_cars, red_flags
            FROM races WHERE circuit_id = ?
            """,
            (circuit_id,),
        )
        if not races:
            return {"races": 0}
        race_ids = tuple(r["id"] for r in races)
        placeholders = ",".join("?" for _ in race_ids)
        dnf_rows = self._results.query(
            f"""
            SELECT COUNT(*) AS dnfs
            FROM results
            WHERE race_id IN ({placeholders}) AND position IS NULL
            """,
            race_ids,
        )
        return {
            "races": len(races),
            "avg_safety_cars": round(
                sum(r["safety_cars"] or 0 for r in races) / len(races), 2
            ),
            "avg_red_flags": round(
                sum(r["red_flags"] or 0 for r in races) / len(races), 2
            ),
            "total_dnfs": dnf_rows[0]["dnfs"] if dnf_rows else 0,
        }

    def grid_importance(self, circuit_id: int) -> float | None:
        """Return the correlation between grid and finishing position.

        A value near 1.0 means qualifying strongly predicts the result (hard to
        overtake); lower values indicate more position change. Returns ``None``
        when there is insufficient data.
        """
        rows = self._results.query(
            """
            SELECT res.grid, res.position
            FROM results res
            JOIN races r ON r.id = res.race_id
            WHERE r.circuit_id = ? AND res.position IS NOT NULL
                  AND res.grid IS NOT NULL AND res.grid > 0
            """,
            (circuit_id,),
        )
        if len(rows) < 3:
            return None
        grids = [r["grid"] for r in rows]
        finishes = [r["position"] for r in rows]
        return _pearson(grids, finishes)

    def pole_conversion(self, circuit_id: int) -> float | None:
        """Return the fraction of races won from pole position at the circuit."""
        rows = self._results.query(
            """
            SELECT res.grid, res.position
            FROM results res
            JOIN races r ON r.id = res.race_id
            WHERE r.circuit_id = ? AND res.grid = 1 AND res.position IS NOT NULL
            """,
            (circuit_id,),
        )
        if not rows:
            return None
        wins_from_pole = sum(1 for r in rows if r["position"] == 1)
        return round(wins_from_pole / len(rows), 4)

    def most_successful_drivers(self, circuit_id: int, limit: int = 5) -> list[dict[str, Any]]:
        """Return the drivers with the most wins at the circuit."""
        return self._results.query(
            """
            SELECT d.full_name AS driver, d.code, COUNT(*) AS wins
            FROM results res
            JOIN races r ON r.id = res.race_id
            JOIN drivers d ON d.id = res.driver_id
            WHERE r.circuit_id = ? AND res.position = 1
            GROUP BY res.driver_id
            ORDER BY wins DESC
            LIMIT ?
            """,
            (circuit_id, int(limit)),
        )

    def most_successful_constructors(self, circuit_id: int, limit: int = 5) -> list[dict[str, Any]]:
        """Return the constructors with the most wins at the circuit."""
        return self._results.query(
            """
            SELECT con.name AS constructor, COUNT(*) AS wins
            FROM results res
            JOIN races r ON r.id = res.race_id
            JOIN constructors con ON con.id = res.constructor_id
            WHERE r.circuit_id = ? AND res.position = 1
            GROUP BY res.constructor_id
            ORDER BY wins DESC
            LIMIT ?
            """,
            (circuit_id, int(limit)),
        )


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Return the Pearson correlation coefficient, or ``None`` if undefined."""
    n = len(xs)
    if n == 0:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return round(cov / (var_x**0.5 * var_y**0.5), 4)
