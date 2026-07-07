"""Odds service — scraping, manual entry and market processing.

Resolves scraped/entered driver names to ``driver_id``, computes implied
probability and market overround, and persists rows to ``odds_history``. Bridges
the scraper layer and the data layer without any UI references.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from calculators import overround as overround_calc
from calculators import probability
from config.logging_config import get_logger
from database.repositories.drivers import DriverRepository
from database.repositories.odds import OddsRepository
from scrapers.odds_scraper import OddsScraper

logger = get_logger(__name__)


class OddsService:
    """Manage odds ingestion, matching and market analytics."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._odds = OddsRepository(db_path=db_path)
        self._drivers = DriverRepository(db_path=db_path)
        self._scraper = OddsScraper()

    # ── Driver matching ──────────────────────────────────────────────
    def resolve_driver(self, name_or_code: str) -> dict[str, Any] | None:
        """Resolve a driver by three-letter code, full name or surname.

        Matching is case-insensitive and tolerant of the messy strings that come
        out of scraped tables. Returns ``None`` when no confident match exists.
        """
        token = (name_or_code or "").strip()
        if not token:
            return None
        by_code = self._drivers.get_by_code(token.upper())
        if by_code:
            return by_code
        lowered = token.lower()
        best: dict[str, Any] | None = None
        for driver in self._drivers.get_all():
            full = driver["full_name"].lower()
            surname = driver["last_name"].lower()
            if lowered == full or lowered == surname:
                return driver
            if surname in lowered or lowered in full:
                best = best or driver
        return best

    # ── Manual entry ─────────────────────────────────────────────────
    def add_manual_odds(
        self,
        race_id: int,
        driver_id: int,
        market: str,
        bookmaker: str,
        decimal_odds: float,
        source_url: str | None = None,
    ) -> int:
        """Insert a single odds row, computing implied probability.

        Returns:
            The new ``odds_history`` row id.

        Raises:
            ValueError: If ``decimal_odds`` is not greater than 1.0.
        """
        if decimal_odds <= 1.0:
            raise ValueError("Decimal odds must be greater than 1.0.")
        record = {
            "race_id": race_id,
            "driver_id": driver_id,
            "market": market,
            "bookmaker": bookmaker,
            "odds_decimal": decimal_odds,
            "odds_fractional": probability.decimal_to_fractional(decimal_odds),
            "odds_american": probability.decimal_to_american(decimal_odds),
            "implied_probability": round(probability.decimal_to_implied(decimal_odds), 6),
            "source_url": source_url,
        }
        return self._odds.insert(record)

    # ── Scraping ─────────────────────────────────────────────────────
    def scrape_and_store(
        self,
        url: str,
        race_id: int,
        market: str = "race_winner",
        bookmaker: str = "scraped",
    ) -> dict[str, Any]:
        """Scrape odds from ``url`` and store rows that match known drivers.

        Args:
            url: Page URL to scrape.
            race_id: Race the odds belong to.
            market: Market label for the scraped rows.
            bookmaker: Bookmaker label for the scraped rows.

        Returns:
            A summary dict: ``stored``, ``unmatched`` (list of names) and
            ``total`` scraped rows.
        """
        records = self._scraper.scrape(url, market=market, bookmaker=bookmaker)
        stored = 0
        unmatched: list[str] = []
        for rec in records:
            driver = self.resolve_driver(rec.driver)
            if driver is None:
                unmatched.append(rec.driver)
                continue
            try:
                self.add_manual_odds(
                    race_id, driver["id"], market, bookmaker, rec.odds_decimal, url
                )
                stored += 1
            except ValueError:
                unmatched.append(rec.driver)
        logger.info(
            "Scraped %s: stored %d, unmatched %d", url, stored, len(unmatched)
        )
        return {"stored": stored, "unmatched": unmatched, "total": len(records)}

    # ── Reads / analytics ────────────────────────────────────────────
    def get_market_table(self, race_id: int, market: str) -> list[dict[str, Any]]:
        """Return odds for a race/market with driver names, best price first."""
        return self._odds.get_by_race_market(race_id, market)

    def market_overround(self, race_id: int, market: str) -> float | None:
        """Return the overround for the best price per driver in a market.

        Uses the shortest (most likely) price per driver so the overround
        reflects a single coherent book. Returns ``None`` with fewer than two
        priced drivers.
        """
        rows = self._odds.get_by_race_market(race_id, market)
        best_by_driver: dict[int, float] = {}
        for row in rows:
            did = row["driver_id"]
            price = row["odds_decimal"]
            if did not in best_by_driver or price < best_by_driver[did]:
                best_by_driver[did] = price
        prices = list(best_by_driver.values())
        if len(prices) < 2:
            return None
        return round(overround_calc.calculate_overround(prices), 6)
