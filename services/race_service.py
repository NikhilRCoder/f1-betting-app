"""Race service — season, race and results orchestration.

Covers the read-side needs of the Historical and Dashboard pages. Upcoming-race
orchestration (odds, predictions) is layered on in Phase 5.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from database.repositories.races import RaceRepository
from database.repositories.results import ResultRepository


class RaceService:
    """High-level race/season read operations for the UI layer."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._races = RaceRepository(db_path=db_path)
        self._results = ResultRepository(db_path=db_path)

    def list_seasons(self) -> list[int]:
        """Return all seasons present in the database, newest first."""
        rows = self._races.query(
            "SELECT DISTINCT season FROM races ORDER BY season DESC"
        )
        return [r["season"] for r in rows]

    def races_for_season(self, season: int) -> list[dict[str, Any]]:
        """Return races in a season with circuit names, ordered by round."""
        return self._races.query(
            """
            SELECT r.*, c.name AS circuit_name, c.country
            FROM races r
            JOIN circuits c ON c.id = r.circuit_id
            WHERE r.season = ?
            ORDER BY r.round
            """,
            (season,),
        )

    def race_results(self, race_id: int) -> list[dict[str, Any]]:
        """Return a race's results with driver and constructor names."""
        return self._results.query(
            """
            SELECT res.position, res.position_text, res.grid, res.points,
                   res.status, d.full_name AS driver, d.code,
                   con.name AS constructor
            FROM results res
            JOIN drivers d ON d.id = res.driver_id
            JOIN constructors con ON con.id = res.constructor_id
            WHERE res.race_id = ?
            ORDER BY (res.position IS NULL), res.position
            """,
            (race_id,),
        )

    def latest_race(self) -> dict[str, Any] | None:
        """Return the most recent race that has results, or ``None``."""
        rows = self._races.query(
            """
            SELECT r.*, c.name AS circuit_name, c.country
            FROM races r
            JOIN circuits c ON c.id = r.circuit_id
            WHERE EXISTS (SELECT 1 FROM results res WHERE res.race_id = r.id)
            ORDER BY r.date DESC
            LIMIT 1
            """
        )
        return rows[0] if rows else None

    def season_driver_standings(self, season: int) -> list[dict[str, Any]]:
        """Return driver points standings for a season, highest first."""
        return self._results.query(
            """
            SELECT d.full_name AS driver, d.code,
                   ROUND(SUM(res.points), 1) AS points,
                   SUM(CASE WHEN res.position = 1 THEN 1 ELSE 0 END) AS wins
            FROM results res
            JOIN races r ON r.id = res.race_id
            JOIN drivers d ON d.id = res.driver_id
            WHERE r.season = ?
            GROUP BY res.driver_id
            ORDER BY points DESC
            """,
            (season,),
        )
