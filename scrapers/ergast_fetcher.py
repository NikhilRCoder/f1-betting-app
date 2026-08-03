"""Jolpica-F1 (Ergast-compatible) API client.

Fetches F1 data from the Jolpica-F1 API — the maintained successor to the
deprecated Ergast API — in the same JSON shape Ergast used. Handles pagination
(``limit``/``offset``/``total``) and polite rate limiting.

The client is transport-only: it returns parsed lists of JSON dicts and knows
nothing about the database. ``database.ergast_import`` maps these into the
schema. ``_get`` is the single network seam, so tests inject fixtures by
substituting it.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from config.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_BASE_URL = "https://api.jolpi.ca/ergast/f1"
_PAGE_LIMIT = 100
_HEADERS = {"User-Agent": "PitWall/0.1 (F1 analytics)"}


class ErgastClient:
    """Paginating client for the Jolpica-F1 / Ergast JSON API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        sleep: float = 0.3,
        timeout: int = 20,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.sleep = sleep
        self.timeout = timeout
        self._session = session or requests.Session()

    # ── Network seam (monkeypatched in tests) ────────────────────────
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch one page and return the ``MRData`` object.

        Raises:
            requests.RequestException: On network/HTTP failure.
        """
        url = f"{self.base_url}/{path}"
        response = self._session.get(
            url, params=params, headers=_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        if self.sleep:
            time.sleep(self.sleep)  # be polite to the shared free API
        return response.json()["MRData"]

    # ── Pagination helpers ───────────────────────────────────────────
    def _paginate_list(self, path: str, table_key: str, list_key: str) -> list[dict[str, Any]]:
        """Concatenate a simple list resource (circuits/drivers/constructors)."""
        offset = 0
        out: list[dict[str, Any]] = []
        while True:
            data = self._get(path, {"limit": _PAGE_LIMIT, "offset": offset})
            items = data.get(table_key, {}).get(list_key, [])
            out.extend(items)
            total = int(data.get("total", 0))
            offset += _PAGE_LIMIT
            if offset >= total or not items:
                break
        return out

    def _paginate_races(self, path: str, sub_key: str) -> list[dict[str, Any]]:
        """Merge a race-nested resource (results/qualifying) across pages.

        Result and qualifying pages split rows across races, so the same race can
        appear on several pages with partial ``sub_key`` lists. Races are merged
        by (season, round) with their sub-lists concatenated.
        """
        offset = 0
        races: dict[tuple[str, str], dict[str, Any]] = {}
        order: list[tuple[str, str]] = []
        while True:
            data = self._get(path, {"limit": _PAGE_LIMIT, "offset": offset})
            items = data.get("RaceTable", {}).get("Races", [])
            for race in items:
                key = (race["season"], race["round"])
                if key not in races:
                    races[key] = race
                    order.append(key)
                else:
                    races[key].setdefault(sub_key, []).extend(race.get(sub_key, []))
            total = int(data.get("total", 0))
            offset += _PAGE_LIMIT
            if offset >= total or not items:
                break
        return [races[k] for k in order]

    # ── Public resource methods ──────────────────────────────────────
    def circuits(self, year: int) -> list[dict[str, Any]]:
        """Return circuits that appear in ``year``."""
        return self._paginate_list(f"{year}/circuits.json", "CircuitTable", "Circuits")

    def drivers(self, year: int) -> list[dict[str, Any]]:
        """Return drivers that competed in ``year``."""
        return self._paginate_list(f"{year}/drivers.json", "DriverTable", "Drivers")

    def constructors(self, year: int) -> list[dict[str, Any]]:
        """Return constructors that competed in ``year``."""
        return self._paginate_list(
            f"{year}/constructors.json", "ConstructorTable", "Constructors"
        )

    def races(self, year: int) -> list[dict[str, Any]]:
        """Return the race schedule for ``year``."""
        return self._paginate_list(f"{year}.json", "RaceTable", "Races")

    def results(self, year: int) -> list[dict[str, Any]]:
        """Return races with nested ``Results`` for ``year``."""
        return self._paginate_races(f"{year}/results.json", "Results")

    def qualifying(self, year: int) -> list[dict[str, Any]]:
        """Return races with nested ``QualifyingResults`` for ``year``."""
        return self._paginate_races(f"{year}/qualifying.json", "QualifyingResults")

    def pitstops(self, year: int, rnd: str | int) -> list[dict[str, Any]]:
        """Return pit stops for a single race (available 2011+)."""
        races = self._paginate_races(f"{year}/{rnd}/pitstops.json", "PitStops")
        return races[0].get("PitStops", []) if races else []
