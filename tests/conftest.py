"""Shared pytest fixtures."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from database.connection import get_connection, initialize_database


@pytest.fixture()
def model_db(tmp_path: Path) -> Path:
    """Build a deterministic multi-race database for model/service tests.

    Five drivers of decreasing skill race twelve times across two seasons, with
    qualifying, occasional DNFs, and bookmaker odds for the final race. Driver 1
    is the strongest, so a well-behaved model should rate it the favourite.
    """
    rng = random.Random(1)
    db = tmp_path / "model.db"
    initialize_database(db)
    skill = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

    with get_connection(db) as conn:
        conn.execute(
            "INSERT INTO circuits (id,name,country,circuit_type) "
            "VALUES (1,'A','X','street'),(2,'B','Y','permanent')"
        )
        for d in range(1, 6):
            conn.execute(
                "INSERT INTO drivers (id,code,first_name,last_name,full_name) "
                "VALUES (?,?,?,?,?)",
                (d, f"D{d}", f"F{d}", f"L{d}", f"F{d} L{d}"),
            )
        conn.execute("INSERT INTO constructors (id,name) VALUES (1,'C1'),(2,'C2')")
        conn.execute("INSERT INTO seasons (year,rounds) VALUES (2023,6),(2024,6)")

        rid = 0
        for season in (2023, 2024):
            for rnd in range(1, 7):
                rid += 1
                cid = 1 if rnd % 2 else 2
                conn.execute(
                    "INSERT INTO races (id,season,round,circuit_id,name,date) "
                    "VALUES (?,?,?,?,?,?)",
                    (rid, season, rnd, cid, f"R{rid}", f"{season}-{rnd:02d}-01"),
                )
                order = sorted(range(1, 6), key=lambda d: skill[d] + rng.random() * 2)
                for pos, d in enumerate(order, start=1):
                    con = 1 if d <= 2 else 2
                    dnf = rng.random() < 0.1
                    conn.execute(
                        "INSERT INTO results "
                        "(race_id,driver_id,constructor_id,grid,position,points,status) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (rid, d, con, pos, None if dnf else pos,
                         0 if dnf else max(0, 26 - pos * 5),
                         "DNF" if dnf else "Finished"),
                    )
                    conn.execute(
                        "INSERT INTO qualifying "
                        "(race_id,driver_id,constructor_id,position,q3_time_ms) "
                        "VALUES (?,?,?,?,?)",
                        (rid, d, con, pos, 80000 + pos * 200),
                    )

        odds = [2.5, 3.5, 5.0, 8.0, 15.0]
        for d in range(1, 6):
            conn.execute(
                "INSERT INTO odds_history "
                "(race_id,driver_id,market,bookmaker,odds_decimal) VALUES (?,?,?,?,?)",
                (12, d, "race_winner", "book", odds[d - 1]),
            )
    return db
