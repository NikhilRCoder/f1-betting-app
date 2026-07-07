"""Generic HTML-table odds parser.

Default parser for odds pages: scans every ``<table>`` on the page and extracts
rows that look like ``(name, decimal-odds)`` pairs. Bookmaker-specific parsers
can subclass or replace this for structured sites.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from config.logging_config import get_logger

logger = get_logger(__name__)

# Matches a plausible decimal-odds token, e.g. "3.50" or "12.0".
_ODDS_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3})?$")


def _looks_like_odds(text: str) -> float | None:
    """Return the float value if ``text`` looks like decimal odds (> 1.0)."""
    token = text.strip().replace(",", ".")
    if _ODDS_RE.match(token):
        value = float(token)
        if value > 1.0:
            return value
    return None


def parse_odds_tables(html: str) -> list[dict[str, Any]]:
    """Extract ``(driver, odds_decimal)`` pairs from all HTML tables.

    The parser is deliberately permissive: for each table row it takes the first
    non-numeric cell as the driver name and the first cell that parses as
    decimal odds as the price.

    Args:
        html: Raw page HTML.

    Returns:
        A list of dicts with ``driver`` and ``odds_decimal`` keys. Empty when no
        odds-like rows are found.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            driver: str | None = None
            odds: float | None = None
            for cell in cells:
                value = _looks_like_odds(cell)
                if value is not None and odds is None:
                    odds = value
                elif cell and driver is None and _looks_like_odds(cell) is None:
                    driver = cell
            if driver and odds is not None:
                records.append({"driver": driver, "odds_decimal": odds})

    logger.info("Generic parser extracted %d odds rows", len(records))
    return records
