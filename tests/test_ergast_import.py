"""Tests for the Jolpica/Ergast API importer, using fixture JSON (no network)."""
from __future__ import annotations

from pathlib import Path

from database.connection import get_connection, initialize_database
from database.ergast_import import import_from_ergast
from database.repositories.drivers import DriverRepository
from database.repositories.qualifying import QualifyingRepository
from database.repositories.results import ResultRepository


class FakeErgastClient:
    """Duck-typed stand-in for ErgastClient returning canned 2024 JSON."""

    def circuits(self, year):
        return [
            {
                "circuitId": "bahrain",
                "circuitName": "Bahrain International Circuit",
                "Location": {"lat": "26.0", "long": "50.5",
                             "locality": "Sakhir", "country": "Bahrain"},
            }
        ]

    def drivers(self, year):
        return [
            {"driverId": "max_verstappen", "code": "VER", "givenName": "Max",
             "familyName": "Verstappen", "dateOfBirth": "1997-09-30",
             "nationality": "Dutch"},
            # No 'code' -> importer must derive a unique one.
            {"driverId": "jack_doe", "givenName": "Jack", "familyName": "Doe",
             "nationality": "British"},
        ]

    def constructors(self, year):
        return [
            {"constructorId": "red_bull", "name": "Red Bull", "nationality": "Austrian"},
            {"constructorId": "mclaren", "name": "McLaren", "nationality": "British"},
        ]

    def races(self, year):
        return [
            {"season": "2024", "round": "1", "raceName": "Bahrain Grand Prix",
             "Circuit": {"circuitId": "bahrain",
                         "circuitName": "Bahrain International Circuit"},
             "date": "2024-03-02", "time": "15:00:00Z"}
        ]

    def results(self, year):
        return [
            {"season": "2024", "round": "1",
             "Results": [
                 {"position": "1", "positionText": "1", "points": "25",
                  "Driver": {"driverId": "max_verstappen"},
                  "Constructor": {"constructorId": "red_bull"},
                  "grid": "1", "laps": "57", "status": "Finished",
                  "Time": {"millis": "5400000", "time": "1:30:00.000"},
                  "FastestLap": {"rank": "1", "Time": {"time": "1:32.608"},
                                 "AverageSpeed": {"speed": "210.5"}}},
                 {"position": "2", "positionText": "R", "points": "0",
                  "Driver": {"driverId": "jack_doe"},
                  "Constructor": {"constructorId": "mclaren"},
                  "grid": "3", "laps": "40", "status": "Engine"},
             ]}
        ]

    def qualifying(self, year):
        return [
            {"season": "2024", "round": "1",
             "QualifyingResults": [
                 {"position": "1", "Driver": {"driverId": "max_verstappen"},
                  "Constructor": {"constructorId": "red_bull"},
                  "Q1": "1:30.100", "Q2": "1:29.900", "Q3": "1:29.100"},
                 {"position": "3", "Driver": {"driverId": "jack_doe"},
                  "Constructor": {"constructorId": "mclaren"}, "Q1": "1:30.500"},
             ]}
        ]

    def pitstops(self, year, rnd):
        return [
            {"driverId": "max_verstappen", "stop": "1", "lap": "20",
             "time": "16:30:00", "duration": "22.5"}
        ]


def test_import_from_ergast(tmp_path: Path):
    db = tmp_path / "api.db"
    initialize_database(db)
    counts = import_from_ergast(
        [2024], db_path=db, client=FakeErgastClient()
    )
    assert counts == {
        "circuits": 1, "drivers": 2, "constructors": 2, "races": 1,
        "results": 2, "qualifying": 2, "pit_stops": 1,
    }

    drivers = DriverRepository(db_path=db)
    assert drivers.get_by_code("VER")["last_name"] == "Verstappen"
    # Missing code was derived (not null) and unique.
    codes = [d["code"] for d in drivers.get_all()]
    assert all(codes) and len(codes) == len(set(codes))

    results = ResultRepository(db_path=db).get_by_race(1)
    winner = next(r for r in results if r["driver_id"] == 1)
    dnf = next(r for r in results if r["driver_id"] == 2)
    assert winner["position"] == 1
    assert winner["time_ms"] == 5400000
    assert dnf["position"] is None          # 'R' -> DNF
    assert dnf["status"] == "Engine"

    quali = QualifyingRepository(db_path=db).get_by_race(1)
    pole = next(q for q in quali if q["driver_id"] == 1)
    assert pole["q3_time_ms"] == 89100      # 1:29.100

    with get_connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM pit_stops").fetchone()["n"] == 1


def test_import_idempotent(tmp_path: Path):
    db = tmp_path / "api2.db"
    initialize_database(db)
    import_from_ergast([2024], db_path=db, client=FakeErgastClient())
    # Re-import must not duplicate races/results.
    import_from_ergast([2024], db_path=db, client=FakeErgastClient())
    with get_connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM races").fetchone()["n"] == 1
        assert conn.execute("SELECT COUNT(*) AS n FROM results").fetchone()["n"] == 2
