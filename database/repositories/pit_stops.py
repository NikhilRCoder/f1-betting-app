"""Pit-stop repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class PitStopRepository(BaseRepository):
    """Data access for the ``pit_stops`` table."""

    table_name = "pit_stops"

    def get_by_race(self, race_id: int) -> list[dict[str, Any]]:
        """Return all pit stops for a race ordered by lap."""
        return self.query(
            "SELECT * FROM pit_stops WHERE race_id = ? ORDER BY lap", (race_id,)
        )

    def get_avg_duration_by_driver(self, driver_id: int) -> float | None:
        """Return a driver's mean pit-stop duration in ms, or ``None``."""
        rows = self.query(
            "SELECT AVG(duration_ms) AS avg_ms FROM pit_stops WHERE driver_id = ?",
            (driver_id,),
        )
        return rows[0]["avg_ms"] if rows else None
