"""Circuit service — orchestration for circuit analysis."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis.circuit_analysis import CircuitAnalyzer
from database.repositories.circuits import CircuitRepository


class CircuitService:
    """High-level circuit operations for the UI layer."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._circuits = CircuitRepository(db_path=db_path)
        self._analyzer = CircuitAnalyzer(db_path=db_path)

    def list_circuits(self) -> list[dict[str, Any]]:
        """Return circuits for selection widgets, ordered by name."""
        return self._circuits.get_all(order_by="name")

    def get_profile(self, circuit_id: int) -> dict[str, Any]:
        """Return a circuit profile: physical stats plus historical analysis.

        Args:
            circuit_id: Circuit primary-key id.

        Returns:
            A dict with ``circuit``, ``characteristics``, ``grid_importance``,
            ``pole_conversion`` and top drivers/constructors. ``circuit`` is
            ``None`` when the id is unknown.
        """
        circuit = self._circuits.get_by_id(circuit_id)
        if circuit is None:
            return {"circuit": None}
        return {
            "circuit": circuit,
            "characteristics": self._analyzer.race_characteristics(circuit_id),
            "grid_importance": self._analyzer.grid_importance(circuit_id),
            "pole_conversion": self._analyzer.pole_conversion(circuit_id),
            "top_drivers": self._analyzer.most_successful_drivers(circuit_id),
            "top_constructors": self._analyzer.most_successful_constructors(circuit_id),
        }
