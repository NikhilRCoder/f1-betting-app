"""Race repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class RaceRepository(BaseRepository):
    """Data access for the ``races`` table."""

    table_name = "races"
    upsert_key = ("season", "round")

    def get_by_season(self, season: int) -> list[dict[str, Any]]:
        """Return all races in a season ordered by round."""
        return self.query(
            "SELECT * FROM races WHERE season = ? ORDER BY round", (season,)
        )

    def get_by_season_round(self, season: int, rnd: int) -> dict[str, Any] | None:
        """Return the race for a specific season and round, or ``None``."""
        return self.find_one(season=season, round=rnd)

    def get_upcoming(self, today: str) -> list[dict[str, Any]]:
        """Return races on or after ``today`` (ISO date), soonest first."""
        return self.query(
            "SELECT * FROM races WHERE date >= ? ORDER BY date ASC", (today,)
        )

    def get_with_circuit(self, race_id: int) -> dict[str, Any] | None:
        """Return a race joined with its circuit details, or ``None``."""
        rows = self.query(
            """
            SELECT r.*, c.name AS circuit_name, c.country, c.circuit_type,
                   c.length_km, c.corners, c.drs_zones
            FROM races r
            JOIN circuits c ON c.id = r.circuit_id
            WHERE r.id = ?
            """,
            (race_id,),
        )
        return rows[0] if rows else None
