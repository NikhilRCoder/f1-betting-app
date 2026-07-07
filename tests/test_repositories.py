"""Tests for the data-access layer against a temporary database."""
from __future__ import annotations

from pathlib import Path

import pytest

from database.connection import initialize_database
from database.repositories.drivers import DriverRepository
from database.repositories.circuits import CircuitRepository


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Create a fresh, schema-initialised temporary database."""
    path = tmp_path / "test.db"
    initialize_database(path)
    return path


def test_insert_and_get(db_path: Path):
    repo = DriverRepository(db_path=db_path)
    new_id = repo.insert(
        {
            "code": "VER",
            "first_name": "Max",
            "last_name": "Verstappen",
            "full_name": "Max Verstappen",
            "nationality": "Dutch",
        }
    )
    assert new_id > 0
    record = repo.get_by_id(new_id)
    assert record is not None
    assert record["code"] == "VER"


def test_find_and_count(db_path: Path):
    repo = DriverRepository(db_path=db_path)
    repo.insert(
        {"code": "NOR", "first_name": "Lando", "last_name": "Norris",
         "full_name": "Lando Norris"}
    )
    assert repo.count() == 1
    assert repo.get_by_code("NOR")["last_name"] == "Norris"
    assert repo.find_one(code="ZZZ") is None


def test_update_and_delete(db_path: Path):
    repo = DriverRepository(db_path=db_path)
    new_id = repo.insert(
        {"code": "HAM", "first_name": "Lewis", "last_name": "Hamilton",
         "full_name": "Lewis Hamilton"}
    )
    assert repo.update(new_id, {"nationality": "British"}) is True
    assert repo.get_by_id(new_id)["nationality"] == "British"
    assert repo.delete(new_id) is True
    assert repo.get_by_id(new_id) is None


def test_upsert_idempotent(db_path: Path):
    repo = CircuitRepository(db_path=db_path)
    data = {"name": "Monaco", "country": "Monaco", "circuit_type": "street"}
    first = repo.upsert(data)
    # Re-upsert with a changed field; row count must stay at 1.
    repo.upsert({**data, "corners": 19})
    assert repo.count() == 1
    updated = repo.get_by_id(first)
    assert updated["corners"] == 19


def test_insert_many(db_path: Path):
    repo = DriverRepository(db_path=db_path)
    n = repo.insert_many(
        [
            {"code": "LEC", "first_name": "Charles", "last_name": "Leclerc",
             "full_name": "Charles Leclerc"},
            {"code": "SAI", "first_name": "Carlos", "last_name": "Sainz",
             "full_name": "Carlos Sainz"},
        ]
    )
    assert n == 2
    assert repo.count() == 2
