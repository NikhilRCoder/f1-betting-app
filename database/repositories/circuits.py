"""Circuit repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class CircuitRepository(BaseRepository):
    """Data access for the ``circuits`` table."""

    table_name = "circuits"
    upsert_key = ("name",)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Return the circuit with the given name, or ``None``."""
        return self.find_one(name=name)

    def get_by_type(self, circuit_type: str) -> list[dict[str, Any]]:
        """Return all circuits of a given type ('street', 'permanent', 'hybrid')."""
        return self.find_by(circuit_type=circuit_type)
