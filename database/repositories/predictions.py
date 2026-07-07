"""Model-predictions repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class PredictionRepository(BaseRepository):
    """Data access for the ``model_predictions`` table."""

    table_name = "model_predictions"

    def get_by_race_model(
        self, race_id: int, model_name: str, market: str
    ) -> list[dict[str, Any]]:
        """Return predictions for a race/model/market, highest probability first."""
        return self.query(
            """
            SELECT p.*, d.full_name AS driver, d.code
            FROM model_predictions p
            JOIN drivers d ON d.id = p.driver_id
            WHERE p.race_id = ? AND p.model_name = ? AND p.market = ?
            ORDER BY p.probability DESC
            """,
            (race_id, model_name, market),
        )

    def get_models_for_race(self, race_id: int) -> list[str]:
        """Return the distinct model names that have predictions for a race."""
        rows = self.query(
            "SELECT DISTINCT model_name FROM model_predictions WHERE race_id = ?",
            (race_id,),
        )
        return [r["model_name"] for r in rows]

    def delete_for_race_model(self, race_id: int, model_name: str) -> int:
        """Delete a model's predictions for a race so it can be re-run. Returns rows removed."""
        with_conn = self.query  # readability alias for the count-after pattern
        before = len(with_conn(
            "SELECT id FROM model_predictions WHERE race_id = ? AND model_name = ?",
            (race_id, model_name),
        ))
        from database.connection import get_connection

        with get_connection(self.db_path) as conn:
            conn.execute(
                "DELETE FROM model_predictions WHERE race_id = ? AND model_name = ?",
                (race_id, model_name),
            )
        return before
