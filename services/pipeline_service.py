"""Race-weekend pipeline — one-call orchestration.

Runs the full pre-race chain for a race: generate recommendations across markets,
collect the value opportunities, optionally produce a pre-race PDF, and optionally
fire an alert. Wraps the existing services; contains no UI references.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from config.logging_config import get_logger
from database.repositories.races import RaceRepository
from services.recommendation_service import RecommendationService
from services.report_service import ReportService
from utilities import notify

logger = get_logger(__name__)

DEFAULT_MARKETS: tuple[str, ...] = ("race_winner", "podium", "top5", "top10")


class WeekendPipeline:
    """Orchestrate recommendations, reporting and alerts for a race."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._recommendations = RecommendationService(db_path=db_path)
        self._reports = ReportService(db_path=db_path)
        self._races = RaceRepository(db_path=db_path)

    def run(
        self,
        race_id: int,
        markets: Sequence[str] = DEFAULT_MARKETS,
        make_pdf: bool = True,
        send_alert: bool = False,
    ) -> dict[str, Any]:
        """Run the weekend pipeline for ``race_id``.

        Args:
            race_id: Target race primary-key id.
            markets: Markets to evaluate (``h2h`` is skipped — it is pairwise).
            make_pdf: Generate a pre-race PDF report.
            send_alert: Send an email alert if STRONG_BETs are found (requires
                SMTP configured; otherwise a no-op).

        Returns:
            A summary dict: per-market recommendation lists and counts,
            ``strong_bets`` across markets, ``pdf_path`` and ``alert_sent``.
        """
        race = self._races.get_by_id(race_id)
        race_name = race["name"] if race else str(race_id)

        by_market: dict[str, list[dict[str, Any]]] = {}
        strong: list[dict[str, Any]] = []
        for market in markets:
            if market == "h2h":
                continue
            recs = self._recommendations.generate_for_race(race_id, market=market)
            by_market[market] = recs
            strong.extend(r for r in recs if r["verdict"] == "STRONG_BET")

        pdf_path: str | None = None
        if make_pdf and any(by_market.values()):
            try:
                pdf_path = str(self._reports.generate_prerace_pdf(race_id))
            except Exception as exc:  # noqa: BLE001 - report is best-effort
                logger.warning("Pre-race PDF generation failed: %s", exc)

        summary: dict[str, Any] = {
            "race_id": race_id,
            "race_name": race_name,
            "markets": by_market,
            "counts": {m: len(v) for m, v in by_market.items()},
            "strong_bets": strong,
            "pdf_path": pdf_path,
            "alert_sent": False,
        }

        if send_alert and strong:
            summary["alert_sent"] = notify.send_email(
                subject=f"PitWall: {len(strong)} value bet(s) — {race_name}",
                body=notify.format_alert(summary),
            )

        logger.info(
            "Weekend pipeline for race %s: %d strong bet(s) across %d market(s).",
            race_id, len(strong), len(by_market),
        )
        return summary
