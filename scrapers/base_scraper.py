"""Abstract scraper interface.

Defines the contract every odds scraper implements: fetch a URL and return a
list of structured odds records. Concrete scrapers delegate HTML parsing to a
parser from :mod:`scrapers.parsers`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import requests

from config.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 15
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PitWall/0.1; +https://example.local/pitwall)"
    )
}


@dataclass
class OddsRecord:
    """A single scraped odds row in a scraper-agnostic shape.

    Attributes:
        driver: Driver name or code as it appeared on the page.
        odds_decimal: Decimal odds.
        market: Betting market (e.g. ``'race_winner'``).
        bookmaker: Source bookmaker name.
        extra: Any additional raw fields captured during parsing.
    """

    driver: str
    odds_decimal: float
    market: str = "race_winner"
    bookmaker: str = "unknown"
    extra: dict[str, Any] = field(default_factory=dict)


class BaseScraper(ABC):
    """Base class for odds scrapers."""

    def fetch(self, url: str) -> str:
        """Fetch raw HTML for ``url``.

        Args:
            url: The page URL to fetch.

        Returns:
            The response body as text.

        Raises:
            requests.RequestException: On network/HTTP failure.
        """
        logger.info("Fetching odds page: %s", url)
        response = requests.get(
            url, headers=_DEFAULT_HEADERS, timeout=_DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.text

    @abstractmethod
    def parse(self, html: str, *, market: str, bookmaker: str) -> list[OddsRecord]:
        """Parse HTML into structured :class:`OddsRecord` rows."""
        ...

    def scrape(
        self, url: str, *, market: str = "race_winner", bookmaker: str = "unknown"
    ) -> list[OddsRecord]:
        """Fetch and parse ``url`` into odds records.

        Args:
            url: Page URL to scrape.
            market: Market label to tag the parsed rows with.
            bookmaker: Bookmaker label to tag the parsed rows with.

        Returns:
            A list of :class:`OddsRecord`.
        """
        html = self.fetch(url)
        return self.parse(html, market=market, bookmaker=bookmaker)
