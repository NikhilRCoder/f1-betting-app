"""Odds-history repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class OddsRepository(BaseRepository):
    """Data access for the ``odds_history`` table."""

    table_name = "odds_history"

    def get_by_race_market(self, race_id: int, market: str) -> list[dict[str, Any]]:
        """Return odds for a race/market joined with driver names, best price first."""
        return self.query(
            """
            SELECT o.*, d.full_name AS driver, d.code
            FROM odds_history o
            JOIN drivers d ON d.id = o.driver_id
            WHERE o.race_id = ? AND o.market = ?
            ORDER BY o.odds_decimal ASC
            """,
            (race_id, market),
        )

    def get_latest_for_driver(
        self, race_id: int, driver_id: int, market: str
    ) -> dict[str, Any] | None:
        """Return the most recently scraped odds for a driver/market, or ``None``."""
        rows = self.query(
            """
            SELECT * FROM odds_history
            WHERE race_id = ? AND driver_id = ? AND market = ?
            ORDER BY scraped_at DESC
            LIMIT 1
            """,
            (race_id, driver_id, market),
        )
        return rows[0] if rows else None

    def get_markets_for_race(self, race_id: int) -> list[str]:
        """Return the distinct markets that have odds for a race."""
        rows = self.query(
            "SELECT DISTINCT market FROM odds_history WHERE race_id = ?",
            (race_id,),
        )
        return [r["market"] for r in rows]
