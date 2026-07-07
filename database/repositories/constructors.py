"""Constructor repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class ConstructorRepository(BaseRepository):
    """Data access for the ``constructors`` table."""

    table_name = "constructors"
    upsert_key = ("name",)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Return the constructor with the given name, or ``None``."""
        return self.find_one(name=name)

    def get_active(self) -> list[dict[str, Any]]:
        """Return all active constructors ordered by name."""
        return self.query(
            "SELECT * FROM constructors WHERE active = 1 ORDER BY name"
        )
