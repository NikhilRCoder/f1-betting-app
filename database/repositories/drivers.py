"""Driver repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class DriverRepository(BaseRepository):
    """Data access for the ``drivers`` table."""

    table_name = "drivers"
    upsert_key = ("code",)

    def get_by_code(self, code: str) -> dict[str, Any] | None:
        """Return the driver with the given three-letter code, or ``None``."""
        return self.find_one(code=code)

    def get_active(self) -> list[dict[str, Any]]:
        """Return all active drivers ordered by surname."""
        return self.query(
            "SELECT * FROM drivers WHERE active = 1 ORDER BY last_name"
        )
