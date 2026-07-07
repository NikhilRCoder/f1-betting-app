"""Report service — CSV/Excel/PDF generation.

Turns database records into downloadable artefacts under ``exports/`` and
``reports/``. CSV/Excel use pandas/openpyxl; the pre-race PDF uses reportlab.
No UI references — pages call these methods and offer the resulting file.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config import settings
from config.logging_config import get_logger
from database.repositories.odds import OddsRepository
from database.repositories.predictions import PredictionRepository
from database.repositories.races import RaceRepository
from database.repositories.recommendations import RecommendationRepository

logger = get_logger(__name__)


def _timestamp() -> str:
    """Return a filename-safe timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class ReportService:
    """Generate CSV, Excel and PDF exports/reports."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._recommendations = RecommendationRepository(db_path=db_path)
        self._odds = OddsRepository(db_path=db_path)
        self._predictions = PredictionRepository(db_path=db_path)
        self._races = RaceRepository(db_path=db_path)
        settings.ensure_directories()

    # ── CSV / Excel ──────────────────────────────────────────────────
    def export_recommendations_csv(self, race_id: int) -> Path:
        """Export a race's recommendations to CSV and return the path."""
        rows = self._recommendations.get_by_race(race_id)
        return self._to_csv(rows, f"recommendations_race{race_id}_{_timestamp()}.csv")

    def export_odds_csv(self, race_id: int) -> Path:
        """Export a race's odds history to CSV and return the path."""
        rows = self._odds.find_by(race_id=race_id)
        return self._to_csv(rows, f"odds_race{race_id}_{_timestamp()}.csv")

    def export_predictions_csv(self, race_id: int) -> Path:
        """Export a race's model predictions to CSV and return the path."""
        rows = self._predictions.find_by(race_id=race_id)
        return self._to_csv(rows, f"predictions_race{race_id}_{_timestamp()}.csv")

    def export_recommendations_excel(self, race_id: int) -> Path:
        """Export a race's recommendations to an .xlsx file and return the path."""
        rows = self._recommendations.get_by_race(race_id)
        path = settings.EXPORTS_DIR / f"recommendations_race{race_id}_{_timestamp()}.xlsx"
        df = pd.DataFrame(rows)
        df.to_excel(path, index=False, sheet_name="recommendations")
        logger.info("Wrote Excel export: %s", path.name)
        return path

    def _to_csv(self, rows: list[dict[str, Any]], filename: str) -> Path:
        """Write ``rows`` to a CSV under exports/ and return the path."""
        path = settings.EXPORTS_DIR / filename
        pd.DataFrame(rows).to_csv(path, index=False)
        logger.info("Wrote CSV export: %s (%d rows)", path.name, len(rows))
        return path

    # ── PDF ──────────────────────────────────────────────────────────
    def generate_prerace_pdf(self, race_id: int) -> Path:
        """Generate a pre-race PDF: race header, predictions and recommendations.

        Args:
            race_id: Target race primary-key id.

        Returns:
            Path to the generated PDF under ``reports/``.

        Raises:
            ValueError: If the race id is unknown.
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )

        race = self._races.get_with_circuit(race_id)
        if race is None:
            raise ValueError(f"Unknown race id {race_id}.")

        path = settings.REPORTS_DIR / f"prerace_race{race_id}_{_timestamp()}.pdf"
        doc = SimpleDocTemplate(str(path), pagesize=A4, title="PitWall pre-race report")
        styles = getSampleStyleSheet()
        story: list[Any] = []

        story.append(Paragraph(f"PitWall — Pre-Race Report", styles["Title"]))
        story.append(
            Paragraph(
                f"{race['name']} ({race['season']}) · {race['circuit_name']}, "
                f"{race['country']} · {race['date']}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 16))

        recs = self._recommendations.get_by_race(race_id)
        if recs:
            story.append(Paragraph("Recommendations", styles["Heading2"]))
            story.append(self._rec_table(recs, Table, TableStyle, colors))
        else:
            story.append(
                Paragraph(
                    "No recommendations generated yet for this race.",
                    styles["Italic"],
                )
            )

        doc.build(story)
        logger.info("Wrote PDF report: %s", path.name)
        return path

    @staticmethod
    def _rec_table(recs, Table, TableStyle, colors):
        """Build a reportlab table from recommendation rows."""
        header = ["Driver", "Model %", "Implied %", "Edge %", "EV", "Conf", "Verdict"]
        data = [header]
        for r in recs:
            data.append(
                [
                    r.get("driver", r["driver_id"]),
                    f"{r['model_probability'] * 100:.1f}",
                    f"{r['implied_probability'] * 100:.1f}",
                    f"{r['edge_pct']:.1f}",
                    f"{r['expected_value']:+.2f}",
                    f"{r['confidence']:.0f}",
                    r["verdict"].replace("_", " "),
                ]
            )
        table = Table(data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111118")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f7")]),
                ]
            )
        )
        return table
