"""Recommendations repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository):
    """Data access for the ``recommendations`` table."""

    table_name = "recommendations"

    def get_by_race(self, race_id: int) -> list[dict[str, Any]]:
        """Return recommendations for a race joined with driver names, best EV first."""
        return self.query(
            """
            SELECT rec.*, d.full_name AS driver, d.code
            FROM recommendations rec
            JOIN drivers d ON d.id = rec.driver_id
            WHERE rec.race_id = ?
            ORDER BY rec.expected_value DESC
            """,
            (race_id,),
        )

    def get_by_verdict(self, race_id: int, verdict: str) -> list[dict[str, Any]]:
        """Return recommendations for a race filtered by verdict."""
        return self.query(
            """
            SELECT rec.*, d.full_name AS driver, d.code
            FROM recommendations rec
            JOIN drivers d ON d.id = rec.driver_id
            WHERE rec.race_id = ? AND rec.verdict = ?
            ORDER BY rec.expected_value DESC
            """,
            (race_id, verdict),
        )

    def get_top(self, limit: int = 3) -> list[dict[str, Any]]:
        """Return the top recommendations across all races by expected value."""
        return self.query(
            """
            SELECT rec.*, d.full_name AS driver, d.code, r.name AS race_name
            FROM recommendations rec
            JOIN drivers d ON d.id = rec.driver_id
            JOIN races r ON r.id = rec.race_id
            WHERE rec.verdict IN ('STRONG_BET', 'SMALL_EDGE')
            ORDER BY rec.expected_value DESC
            LIMIT ?
            """,
            (int(limit),),
        )
