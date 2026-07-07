"""Concrete odds scraper using the generic table parser.

Turns a URL into a list of :class:`~scrapers.base_scraper.OddsRecord` by
delegating HTML parsing to :func:`scrapers.parsers.generic_parser.parse_odds_tables`.
"""
from __future__ import annotations

from scrapers.base_scraper import BaseScraper, OddsRecord
from scrapers.parsers.generic_parser import parse_odds_tables


class OddsScraper(BaseScraper):
    """Generic odds scraper backed by the HTML-table parser."""

    def parse(self, html: str, *, market: str, bookmaker: str) -> list[OddsRecord]:
        """Parse HTML into odds records using the generic table parser.

        Args:
            html: Raw page HTML.
            market: Market label applied to every parsed row.
            bookmaker: Bookmaker label applied to every parsed row.

        Returns:
            A list of :class:`OddsRecord`.
        """
        rows = parse_odds_tables(html)
        return [
            OddsRecord(
                driver=row["driver"],
                odds_decimal=row["odds_decimal"],
                market=market,
                bookmaker=bookmaker,
            )
            for row in rows
        ]
