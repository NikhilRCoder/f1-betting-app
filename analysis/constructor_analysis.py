"""Constructor analytical computations.

``ConstructorAnalyzer`` derives team form, reliability and pit-stop metrics from
the database.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from database.repositories.pit_stops import PitStopRepository
from database.repositories.results import ResultRepository


class ConstructorAnalyzer:
    """Compute constructor statistics from historical results."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._results = ResultRepository(db_path=db_path)
        self._pit_stops = PitStopRepository(db_path=db_path)
        self._db_path = db_path

    def season_form(self, constructor_id: int, season: int) -> dict[str, Any]:
        """Return a constructor's aggregate results for one season."""
        rows = self._results.query(
            """
            SELECT res.position, res.points
            FROM results res
            JOIN races r ON r.id = res.race_id
            WHERE res.constructor_id = ? AND r.season = ?
            """,
            (constructor_id, season),
        )
        positions = [r["position"] for r in rows]
        classified = [p for p in positions if p is not None]
        return {
            "season": season,
            "entries": len(rows),
            "points": round(sum(r["points"] or 0 for r in rows), 1),
            "wins": sum(1 for p in classified if p == 1),
            "podiums": sum(1 for p in classified if p <= 3),
            "avg_finish": round(sum(classified) / len(classified), 2)
            if classified
            else None,
        }

    def reliability_rate(self, constructor_id: int) -> float:
        """Return the fraction of entries that were classified finishers."""
        rows = self._results.query(
            "SELECT position FROM results WHERE constructor_id = ?",
            (constructor_id,),
        )
        if not rows:
            return 0.0
        finished = sum(1 for r in rows if r["position"] is not None)
        return round(finished / len(rows), 4)

    def pit_stop_performance(self, constructor_id: int) -> dict[str, Any]:
        """Return pit-stop duration stats (ms) across the team's drivers.

        Joins pit stops to results to attribute stops to the constructor for
        each race.
        """
        rows = self._results.query(
            """
            SELECT ps.duration_ms
            FROM pit_stops ps
            JOIN results res
              ON res.race_id = ps.race_id AND res.driver_id = ps.driver_id
            WHERE res.constructor_id = ? AND ps.duration_ms IS NOT NULL
            """,
            (constructor_id,),
        )
        durations = [r["duration_ms"] for r in rows]
        if not durations:
            return {"avg_ms": None, "best_ms": None, "worst_ms": None, "count": 0}
        return {
            "avg_ms": round(sum(durations) / len(durations), 1),
            "best_ms": min(durations),
            "worst_ms": max(durations),
            "count": len(durations),
        }

    def track_type_suitability(self, constructor_id: int) -> dict[str, float]:
        """Return mean finishing position grouped by circuit type."""
        rows = self._results.query(
            """
            SELECT c.circuit_type AS type, AVG(res.position) AS avg_finish
            FROM results res
            JOIN races r ON r.id = res.race_id
            JOIN circuits c ON c.id = r.circuit_id
            WHERE res.constructor_id = ? AND res.position IS NOT NULL
            GROUP BY c.circuit_type
            """,
            (constructor_id,),
        )
        return {
            r["type"] or "unknown": round(r["avg_finish"], 2)
            for r in rows
            if r["avg_finish"] is not None
        }
