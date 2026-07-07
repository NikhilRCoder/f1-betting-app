"""Qualifying repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class QualifyingRepository(BaseRepository):
    """Data access for the ``qualifying`` table."""

    table_name = "qualifying"

    def get_by_race(self, race_id: int) -> list[dict[str, Any]]:
        """Return all qualifying rows for a race ordered by grid position."""
        return self.query(
            """
            SELECT * FROM qualifying
            WHERE race_id = ?
            ORDER BY (position IS NULL), position
            """,
            (race_id,),
        )

    def get_by_driver(self, driver_id: int, limit: int | None = None) -> list[dict[str, Any]]:
        """Return a driver's qualifying results, most recent race first."""
        sql = """
            SELECT q.*, r.season, r.round, r.date, r.circuit_id
            FROM qualifying q
            JOIN races r ON r.id = q.race_id
            WHERE q.driver_id = ?
            ORDER BY r.date DESC
        """
        params: tuple[Any, ...] = (driver_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (driver_id, int(limit))
        return self.query(sql, params)
