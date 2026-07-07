"""Race-results repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class ResultRepository(BaseRepository):
    """Data access for the ``results`` table."""

    table_name = "results"

    def get_by_race(self, race_id: int) -> list[dict[str, Any]]:
        """Return all results for a race ordered by finishing position."""
        return self.query(
            """
            SELECT * FROM results
            WHERE race_id = ?
            ORDER BY (position IS NULL), position
            """,
            (race_id,),
        )

    def get_by_driver(self, driver_id: int, limit: int | None = None) -> list[dict[str, Any]]:
        """Return a driver's results, most recent race first."""
        sql = """
            SELECT res.*, r.season, r.round, r.date, r.circuit_id
            FROM results res
            JOIN races r ON r.id = res.race_id
            WHERE res.driver_id = ?
            ORDER BY r.date DESC
        """
        params: tuple[Any, ...] = (driver_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (driver_id, int(limit))
        return self.query(sql, params)

    def get_by_driver_at_circuit(
        self, driver_id: int, circuit_id: int
    ) -> list[dict[str, Any]]:
        """Return a driver's results at a specific circuit, newest first."""
        return self.query(
            """
            SELECT res.*, r.season, r.round, r.date
            FROM results res
            JOIN races r ON r.id = res.race_id
            WHERE res.driver_id = ? AND r.circuit_id = ?
            ORDER BY r.date DESC
            """,
            (driver_id, circuit_id),
        )

    def get_winners_at_circuit(self, circuit_id: int) -> list[dict[str, Any]]:
        """Return winning results at a circuit joined with driver names."""
        return self.query(
            """
            SELECT r.season, d.full_name AS driver, d.code, res.constructor_id
            FROM results res
            JOIN races r ON r.id = res.race_id
            JOIN drivers d ON d.id = res.driver_id
            WHERE r.circuit_id = ? AND res.position = 1
            ORDER BY r.season DESC
            """,
            (circuit_id,),
        )
