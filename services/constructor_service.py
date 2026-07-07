"""Constructor service — orchestration for constructor analysis."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis.constructor_analysis import ConstructorAnalyzer
from database.repositories.constructors import ConstructorRepository


class ConstructorService:
    """High-level constructor operations for the UI layer."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._constructors = ConstructorRepository(db_path=db_path)
        self._analyzer = ConstructorAnalyzer(db_path=db_path)

    def list_constructors(self, active_only: bool = False) -> list[dict[str, Any]]:
        """Return constructors for selection widgets, ordered by name."""
        if active_only:
            return self._constructors.get_active()
        return self._constructors.get_all(order_by="name")

    def get_profile(self, constructor_id: int, season: int | None = None) -> dict[str, Any]:
        """Return a constructor profile: reliability, pit stops, track suitability.

        Args:
            constructor_id: Constructor primary-key id.
            season: Optional season for season-specific form.

        Returns:
            A dict with ``constructor``, ``reliability``, ``pit_stops``,
            ``track_type`` and (optionally) ``season_form`` sections.
        """
        constructor = self._constructors.get_by_id(constructor_id)
        if constructor is None:
            return {"constructor": None}
        profile: dict[str, Any] = {
            "constructor": constructor,
            "reliability": self._analyzer.reliability_rate(constructor_id),
            "pit_stops": self._analyzer.pit_stop_performance(constructor_id),
            "track_type": self._analyzer.track_type_suitability(constructor_id),
        }
        if season is not None:
            profile["season_form"] = self._analyzer.season_form(constructor_id, season)
        return profile
