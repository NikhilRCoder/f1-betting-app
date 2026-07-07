"""Driver analytical computations.

``DriverAnalyzer`` derives career and form metrics for a driver directly from the
database. It owns the repositories it needs and returns plain dicts/lists so the
service and UI layers stay decoupled from the data layer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis import form_calculator
from database.repositories.qualifying import QualifyingRepository
from database.repositories.results import ResultRepository


class DriverAnalyzer:
    """Compute driver statistics and form from historical results."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._results = ResultRepository(db_path=db_path)
        self._qualifying = QualifyingRepository(db_path=db_path)
        self._db_path = db_path

    # ── Career & season ──────────────────────────────────────────────
    def career_stats(self, driver_id: int) -> dict[str, Any]:
        """Return aggregate career statistics for a driver.

        Args:
            driver_id: Driver primary-key id.

        Returns:
            A dict of career totals: starts, wins, podiums, points, poles,
            best finish and DNF rate.
        """
        results = self._results.get_by_driver(driver_id)
        poles = self._qualifying.query(
            "SELECT COUNT(*) AS n FROM qualifying WHERE driver_id = ? AND position = 1",
            (driver_id,),
        )[0]["n"]
        positions = [r["position"] for r in results]
        classified = [p for p in positions if p is not None]
        return {
            "starts": len(results),
            "wins": sum(1 for p in classified if p == 1),
            "podiums": sum(1 for p in classified if p <= 3),
            "points_finishes": sum(1 for p in classified if p <= 10),
            "total_points": round(sum(r["points"] or 0 for r in results), 1),
            "poles": poles,
            "best_finish": min(classified) if classified else None,
            "dnf_rate": round(form_calculator.dnf_rate(positions), 4),
        }

    def season_stats(self, driver_id: int, season: int) -> dict[str, Any]:
        """Return a driver's statistics for a single season."""
        rows = self._results.query(
            """
            SELECT res.position, res.points
            FROM results res
            JOIN races r ON r.id = res.race_id
            WHERE res.driver_id = ? AND r.season = ?
            """,
            (driver_id, season),
        )
        positions = [r["position"] for r in rows]
        classified = [p for p in positions if p is not None]
        return {
            "season": season,
            "starts": len(rows),
            "wins": sum(1 for p in classified if p == 1),
            "podiums": sum(1 for p in classified if p <= 3),
            "points": round(sum(r["points"] or 0 for r in rows), 1),
            "best_finish": min(classified) if classified else None,
        }

    # ── Form ─────────────────────────────────────────────────────────
    def current_form(self, driver_id: int, window: int = 5) -> dict[str, Any]:
        """Return recent-form metrics over the last ``window`` races.

        Results are ordered oldest → newest so momentum reads correctly.
        """
        recent = self._results.get_by_driver(driver_id, limit=window)
        positions = [r["position"] for r in reversed(recent)]  # oldest → newest
        return {
            "window": window,
            "recent_positions": positions,
            "avg_finish": form_calculator.rolling_average(positions, window),
            "momentum": round(form_calculator.momentum(positions), 3),
            "form_score": round(form_calculator.form_score(positions, window), 1),
            "points_streak": form_calculator.streak(
                [p is not None and p <= 10 for p in positions]
            ),
        }

    # ── Splits ───────────────────────────────────────────────────────
    def performance_by_circuit_type(self, driver_id: int) -> dict[str, float]:
        """Return mean finishing position grouped by circuit type."""
        rows = self._results.query(
            """
            SELECT c.circuit_type AS type, AVG(res.position) AS avg_finish
            FROM results res
            JOIN races r ON r.id = res.race_id
            JOIN circuits c ON c.id = r.circuit_id
            WHERE res.driver_id = ? AND res.position IS NOT NULL
            GROUP BY c.circuit_type
            """,
            (driver_id,),
        )
        return {
            r["type"] or "unknown": round(r["avg_finish"], 2)
            for r in rows
            if r["avg_finish"] is not None
        }

    def positions_gained(self, driver_id: int) -> dict[str, Any]:
        """Return grid-to-finish delta stats (positive = places gained)."""
        rows = self._results.query(
            """
            SELECT grid, position FROM results
            WHERE driver_id = ? AND position IS NOT NULL
                  AND grid IS NOT NULL AND grid > 0
            """,
            (driver_id,),
        )
        deltas = [r["grid"] - r["position"] for r in rows]
        if not deltas:
            return {"avg_gain": None, "deltas": []}
        return {
            "avg_gain": round(sum(deltas) / len(deltas), 2),
            "best_gain": max(deltas),
            "deltas": deltas,
        }

    def recent_results(self, driver_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Return a driver's most recent results with race context."""
        return self._results.get_by_driver(driver_id, limit=limit)

    def head_to_head(self, driver_id: int, other_id: int) -> dict[str, Any]:
        """Compare two drivers across races they both finished.

        Args:
            driver_id: The primary driver.
            other_id: The comparison driver.

        Returns:
            A dict with each driver's win count in shared, classified races.
        """
        rows = self._results.query(
            """
            SELECT a.race_id,
                   a.position AS pos_a,
                   b.position AS pos_b
            FROM results a
            JOIN results b ON a.race_id = b.race_id
            WHERE a.driver_id = ? AND b.driver_id = ?
                  AND a.position IS NOT NULL AND b.position IS NOT NULL
            """,
            (driver_id, other_id),
        )
        a_wins = sum(1 for r in rows if r["pos_a"] < r["pos_b"])
        b_wins = sum(1 for r in rows if r["pos_b"] < r["pos_a"])
        return {
            "shared_races": len(rows),
            "driver_wins": a_wins,
            "other_wins": b_wins,
        }
