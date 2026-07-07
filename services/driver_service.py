"""Driver service — orchestration for driver analysis.

Wires the driver/qualifying analyzers and repositories into UI-ready structures.
Contains no Streamlit references; pages consume the returned dicts/lists.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis.driver_analysis import DriverAnalyzer
from analysis.qualifying_analysis import QualifyingAnalyzer
from database.repositories.drivers import DriverRepository
from utilities.helpers import clamp, safe_div


class DriverService:
    """High-level driver operations for the UI layer."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._drivers = DriverRepository(db_path=db_path)
        self._analyzer = DriverAnalyzer(db_path=db_path)
        self._qualifying = QualifyingAnalyzer(db_path=db_path)

    def list_drivers(self, active_only: bool = False) -> list[dict[str, Any]]:
        """Return drivers for selection widgets, ordered by surname."""
        if active_only:
            return self._drivers.get_active()
        return self._drivers.get_all(order_by="last_name")

    def get_profile(self, driver_id: int) -> dict[str, Any]:
        """Return a full driver profile combining career, form and qualifying.

        Args:
            driver_id: Driver primary-key id.

        Returns:
            A dict with ``driver``, ``career``, ``form``, ``qualifying``,
            ``circuit_type`` and ``positions_gained`` sections. ``driver`` is
            ``None`` when the id is unknown.
        """
        driver = self._drivers.get_by_id(driver_id)
        if driver is None:
            return {"driver": None}
        return {
            "driver": driver,
            "career": self._analyzer.career_stats(driver_id),
            "form": self._analyzer.current_form(driver_id),
            "qualifying": self._qualifying.summary(driver_id),
            "circuit_type": self._analyzer.performance_by_circuit_type(driver_id),
            "positions_gained": self._analyzer.positions_gained(driver_id),
            "recent_results": self._analyzer.recent_results(driver_id, limit=10),
        }

    def radar_metrics(self, driver_id: int) -> dict[str, float]:
        """Return normalised 0-100 skill metrics for a radar chart.

        Metrics are derived from available results/qualifying data:
        qualifying, race pace, consistency, overtaking, reliability and
        points-scoring. All are scaled so higher is better.
        """
        career = self._analyzer.career_stats(driver_id)
        qual = self._qualifying.summary(driver_id)
        gained = self._analyzer.positions_gained(driver_id)
        form = self._analyzer.current_form(driver_id)

        field = 20.0
        qualifying = self._position_to_score(qual.get("avg_position"), field)
        race_pace = self._position_to_score(form.get("avg_finish"), field)
        reliability = clamp((1.0 - career["dnf_rate"]) * 100.0, 0.0, 100.0)
        points_scoring = clamp(
            safe_div(career["points_finishes"], career["starts"]) * 100.0, 0.0, 100.0
        )
        overtaking = clamp(50.0 + (gained.get("avg_gain") or 0.0) * 10.0, 0.0, 100.0)
        # Consistency: reward a high recent form score.
        consistency = clamp(form.get("form_score", 0.0), 0.0, 100.0)

        return {
            "Qualifying": round(qualifying, 1),
            "Race Pace": round(race_pace, 1),
            "Consistency": round(consistency, 1),
            "Overtaking": round(overtaking, 1),
            "Reliability": round(reliability, 1),
            "Points Scoring": round(points_scoring, 1),
        }

    def head_to_head(self, driver_id: int, other_id: int) -> dict[str, Any]:
        """Return a head-to-head comparison between two drivers."""
        return self._analyzer.head_to_head(driver_id, other_id)

    @staticmethod
    def _position_to_score(avg_position: float | None, field: float) -> float:
        """Map an average finishing/grid position to a 0-100 score."""
        if avg_position is None:
            return 0.0
        return clamp((field - min(avg_position, field)) / (field - 1) * 100.0, 0.0, 100.0)
