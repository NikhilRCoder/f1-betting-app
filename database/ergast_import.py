"""Import F1 data from the Jolpica-F1 API into the schema.

Orchestrates :class:`scrapers.ergast_fetcher.ErgastClient` and the repositories
to pull a range of seasons and populate the database. Unlike the CSV seeder,
the API uses string reference ids (``"max_verstappen"``, ``"red_bull"``), so
entities are upserted by their natural keys and foreign keys are resolved via
ref → id maps built during the import.

The client is injectable, so the full mapping is tested against fixture JSON
without any network access.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

from config.logging_config import get_logger
from database.connection import get_connection
from database.repositories.circuits import CircuitRepository
from database.repositories.constructors import ConstructorRepository
from database.repositories.drivers import DriverRepository
from database.repositories.pit_stops import PitStopRepository
from database.repositories.qualifying import QualifyingRepository
from database.repositories.races import RaceRepository
from database.repositories.results import ResultRepository
from database.seed import _clean, _time_to_ms, _to_int
from scrapers.ergast_fetcher import ErgastClient

logger = get_logger(__name__)

ProgressCallback = Callable[[str], None]


def _derive_code(existing: set[str], code: str | None, surname: str) -> str:
    """Return a unique, non-null driver code (schema requires NOT NULL UNIQUE)."""
    base = (code or "".join(ch for ch in surname.upper() if ch.isalpha())[:3] or "DRV")
    candidate = base
    suffix = 1
    while candidate in existing:
        suffix += 1
        candidate = f"{base}{suffix}"
    existing.add(candidate)
    return candidate


class ErgastImporter:
    """Fetch seasons from the API and write them into the database."""

    def __init__(self, db_path: Path | None = None, client: ErgastClient | None = None) -> None:
        self._client = client or ErgastClient()
        self._db_path = db_path
        self._drivers = DriverRepository(db_path=db_path)
        self._constructors = ConstructorRepository(db_path=db_path)
        self._circuits = CircuitRepository(db_path=db_path)
        self._races = RaceRepository(db_path=db_path)
        self._results = ResultRepository(db_path=db_path)
        self._qualifying = QualifyingRepository(db_path=db_path)
        self._pit_stops = PitStopRepository(db_path=db_path)
        # ref -> our integer id
        self._circuit_ids: dict[str, int] = {}
        self._driver_ids: dict[str, int] = {}
        self._constructor_ids: dict[str, int] = {}
        self._used_codes: set[str] = set()

    def import_seasons(
        self,
        years: Iterable[int],
        include_pitstops: bool = True,
        progress: ProgressCallback | None = None,
    ) -> dict[str, int]:
        """Import the given seasons and return per-table row counts.

        Args:
            years: Seasons to import (e.g. ``range(2021, 2025)``).
            include_pitstops: Fetch per-race pit stops (2011+); adds one request
                per race, so it can be disabled for speed.
            progress: Optional callback invoked with human-readable status lines.

        Returns:
            A mapping of table name to rows written/updated.
        """
        counts: dict[str, int] = {
            "circuits": 0, "drivers": 0, "constructors": 0, "races": 0,
            "results": 0, "qualifying": 0, "pit_stops": 0,
        }

        def _note(msg: str) -> None:
            logger.info(msg)
            if progress:
                progress(msg)

        for year in years:
            _note(f"Fetching {year}: reference data…")
            self._import_circuits(year, counts)
            self._import_drivers(year, counts)
            self._import_constructors(year, counts)

            _note(f"Fetching {year}: races…")
            round_to_race = self._import_races(year, counts)

            _note(f"Fetching {year}: results & qualifying…")
            self._import_results(year, round_to_race, counts)
            self._import_qualifying(year, round_to_race, counts)

            if include_pitstops:
                _note(f"Fetching {year}: pit stops…")
                self._import_pitstops(year, round_to_race, counts)

        _note("Import complete.")
        return counts

    # ── Reference entities ───────────────────────────────────────────
    def _import_circuits(self, year: int, counts: dict[str, int]) -> None:
        for c in self._client.circuits(year):
            ref = c["circuitId"]
            if ref in self._circuit_ids:
                continue
            loc = c.get("Location", {})
            cid = self._circuits.upsert(
                {
                    "name": c["circuitName"],
                    "country": _clean(loc.get("country")) or "Unknown",
                    "city": _clean(loc.get("locality")),
                    "latitude": _clean(loc.get("lat")),
                    "longitude": _clean(loc.get("long")),
                }
            )
            self._circuit_ids[ref] = cid
            counts["circuits"] += 1

    def _import_drivers(self, year: int, counts: dict[str, int]) -> None:
        for d in self._client.drivers(year):
            ref = d["driverId"]
            if ref in self._driver_ids:
                continue
            surname = _clean(d.get("familyName")) or ""
            forename = _clean(d.get("givenName")) or ""
            code = _derive_code(self._used_codes, _clean(d.get("code")), surname)
            did = self._drivers.upsert(
                {
                    "code": code,
                    "first_name": forename,
                    "last_name": surname,
                    "full_name": f"{forename} {surname}".strip(),
                    "nationality": _clean(d.get("nationality")),
                    "date_of_birth": _clean(d.get("dateOfBirth")),
                }
            )
            self._driver_ids[ref] = did
            counts["drivers"] += 1

    def _import_constructors(self, year: int, counts: dict[str, int]) -> None:
        for c in self._client.constructors(year):
            ref = c["constructorId"]
            if ref in self._constructor_ids:
                continue
            cid = self._constructors.upsert(
                {"name": c["name"], "nationality": _clean(c.get("nationality"))}
            )
            self._constructor_ids[ref] = cid
            counts["constructors"] += 1

    # ── Races ────────────────────────────────────────────────────────
    def _import_races(self, year: int, counts: dict[str, int]) -> dict[str, int]:
        """Import the schedule; return a round → race_id map for the season."""
        round_to_race: dict[str, int] = {}
        schedule = self._client.races(year)
        # Season must exist before races (races.season -> seasons.year FK).
        with get_connection(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO seasons (year, rounds) VALUES (?, ?)",
                (year, len(schedule)),
            )
        for r in schedule:
            circuit_ref = r["Circuit"]["circuitId"]
            circuit_id = self._circuit_ids.get(circuit_ref)
            if circuit_id is None:  # circuit not seen in the circuits list
                circuit_id = self._circuits.upsert(
                    {"name": r["Circuit"]["circuitName"], "country": "Unknown"}
                )
                self._circuit_ids[circuit_ref] = circuit_id
            race_id = self._races.upsert(
                {
                    "season": _to_int(r["season"]),
                    "round": _to_int(r["round"]),
                    "circuit_id": circuit_id,
                    "name": r["raceName"],
                    "date": _clean(r.get("date")),
                    "time": _clean(r.get("time")),
                }
            )
            round_to_race[str(r["round"])] = race_id
            counts["races"] += 1
        return round_to_race

    # ── Results / qualifying / pit stops ─────────────────────────────
    def _import_results(
        self, year: int, round_to_race: dict[str, int], counts: dict[str, int]
    ) -> None:
        for race in self._client.results(year):
            race_id = round_to_race.get(str(race["round"]))
            if race_id is None:
                continue
            self._results.query(
                "DELETE FROM results WHERE race_id = ?", (race_id,)
            )
            for row in race.get("Results", []):
                driver_id = self._driver_ids.get(row["Driver"]["driverId"])
                constructor_id = self._constructor_ids.get(
                    row["Constructor"]["constructorId"]
                )
                if driver_id is None or constructor_id is None:
                    continue
                self._results.insert(self._map_result(row, race_id, driver_id, constructor_id))
                counts["results"] += 1

    def _import_qualifying(
        self, year: int, round_to_race: dict[str, int], counts: dict[str, int]
    ) -> None:
        for race in self._client.qualifying(year):
            race_id = round_to_race.get(str(race["round"]))
            if race_id is None:
                continue
            self._qualifying.query(
                "DELETE FROM qualifying WHERE race_id = ?", (race_id,)
            )
            for row in race.get("QualifyingResults", []):
                driver_id = self._driver_ids.get(row["Driver"]["driverId"])
                constructor_id = self._constructor_ids.get(
                    row["Constructor"]["constructorId"]
                )
                if driver_id is None or constructor_id is None:
                    continue
                self._qualifying.insert(
                    {
                        "race_id": race_id,
                        "driver_id": driver_id,
                        "constructor_id": constructor_id,
                        "position": _to_int(row.get("position")),
                        "q1_time_ms": _time_to_ms(row.get("Q1")),
                        "q2_time_ms": _time_to_ms(row.get("Q2")),
                        "q3_time_ms": _time_to_ms(row.get("Q3")),
                    }
                )
                counts["qualifying"] += 1

    def _import_pitstops(
        self, year: int, round_to_race: dict[str, int], counts: dict[str, int]
    ) -> None:
        for rnd, race_id in round_to_race.items():
            try:
                stops = self._client.pitstops(year, rnd)
            except Exception as exc:  # noqa: BLE001 - pit stops missing pre-2011
                logger.warning("Pit stops unavailable for %s round %s: %s", year, rnd, exc)
                continue
            self._pit_stops.query(
                "DELETE FROM pit_stops WHERE race_id = ?", (race_id,)
            )
            for row in stops:
                driver_id = self._driver_ids.get(row.get("driverId"))
                if driver_id is None:
                    continue
                duration = _clean(row.get("duration"))
                duration_ms = None
                try:
                    duration_ms = float(duration) * 1000 if duration else None
                except (TypeError, ValueError):
                    duration_ms = None
                self._pit_stops.insert(
                    {
                        "race_id": race_id,
                        "driver_id": driver_id,
                        "stop_number": _to_int(row.get("stop")),
                        "lap": _to_int(row.get("lap")),
                        "duration_ms": duration_ms,
                        "total_time_ms": duration_ms,
                    }
                )
                counts["pit_stops"] += 1

    @staticmethod
    def _map_result(
        row: dict[str, Any], race_id: int, driver_id: int, constructor_id: int
    ) -> dict[str, Any]:
        """Map one API result row to the ``results`` schema."""
        position_text = str(row.get("positionText", ""))
        position = int(position_text) if position_text.isdigit() else None
        time_obj = row.get("Time") or {}
        fastest = row.get("FastestLap") or {}
        fl_time = (fastest.get("Time") or {}).get("time")
        fl_speed = (fastest.get("AverageSpeed") or {}).get("speed")
        return {
            "race_id": race_id,
            "driver_id": driver_id,
            "constructor_id": constructor_id,
            "grid": _to_int(row.get("grid")),
            "position": position,
            "position_text": position_text or None,
            "points": float(row.get("points", 0) or 0),
            "laps_completed": _to_int(row.get("laps")),
            "status": _clean(row.get("status")),
            "time_ms": _to_int(time_obj.get("millis")),
            "fastest_lap_rank": _to_int(fastest.get("rank")),
            "fastest_lap_time_ms": _time_to_ms(fl_time),
            "fastest_lap_speed": _clean(fl_speed),
        }


def import_from_ergast(
    years: Iterable[int],
    db_path: Path | None = None,
    client: ErgastClient | None = None,
    include_pitstops: bool = True,
    progress: ProgressCallback | None = None,
) -> dict[str, int]:
    """Convenience wrapper: import ``years`` via a fresh :class:`ErgastImporter`."""
    return ErgastImporter(db_path=db_path, client=client).import_seasons(
        years, include_pitstops=include_pitstops, progress=progress
    )
