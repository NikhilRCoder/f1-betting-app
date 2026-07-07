"""Qualifying analytical computations.

``QualifyingAnalyzer`` derives qualifying-specific metrics for a driver: average
grid slot, Q3 appearance rate, pole rate and gap-to-pole.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from database.repositories.qualifying import QualifyingRepository


class QualifyingAnalyzer:
    """Compute qualifying metrics from historical qualifying sessions."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._qualifying = QualifyingRepository(db_path=db_path)
        self._db_path = db_path

    def summary(self, driver_id: int) -> dict[str, Any]:
        """Return aggregate qualifying metrics for a driver.

        Args:
            driver_id: Driver primary-key id.

        Returns:
            A dict with session count, average grid, Q3 rate and pole rate.
        """
        rows = self._qualifying.query(
            "SELECT position, q3_time_ms FROM qualifying WHERE driver_id = ?",
            (driver_id,),
        )
        if not rows:
            return {
                "sessions": 0,
                "avg_position": None,
                "q3_rate": None,
                "pole_rate": None,
            }
        positions = [r["position"] for r in rows if r["position"] is not None]
        q3_appearances = sum(1 for r in rows if r["q3_time_ms"] is not None)
        poles = sum(1 for p in positions if p == 1)
        return {
            "sessions": len(rows),
            "avg_position": round(sum(positions) / len(positions), 2)
            if positions
            else None,
            "q3_rate": round(q3_appearances / len(rows), 4),
            "pole_rate": round(poles / len(rows), 4),
        }

    def avg_gap_to_pole(self, driver_id: int) -> float | None:
        """Return the driver's mean percentage gap to pole across sessions.

        For each session the driver's best available time is compared with that
        session's pole time; the percentage gaps are averaged. Returns ``None``
        when no comparable sessions exist.
        """
        sessions = self._qualifying.query(
            """
            SELECT q.race_id,
                   MIN(COALESCE(q.q3_time_ms, q.q2_time_ms, q.q1_time_ms)) AS pole_ms
            FROM qualifying q
            GROUP BY q.race_id
            """,
        )
        pole_by_race = {s["race_id"]: s["pole_ms"] for s in sessions if s["pole_ms"]}

        driver_rows = self._qualifying.query(
            """
            SELECT race_id,
                   COALESCE(q3_time_ms, q2_time_ms, q1_time_ms) AS best_ms
            FROM qualifying WHERE driver_id = ?
            """,
            (driver_id,),
        )
        gaps = []
        for row in driver_rows:
            pole = pole_by_race.get(row["race_id"])
            best = row["best_ms"]
            if pole and best and pole > 0:
                gaps.append((best - pole) / pole * 100.0)
        if not gaps:
            return None
        return round(sum(gaps) / len(gaps), 3)
