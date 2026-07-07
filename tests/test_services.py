"""Tests for the analysis + service layers against a seeded temporary database."""
from __future__ import annotations

from pathlib import Path

import pytest

from analysis import form_calculator
from database.connection import get_connection, initialize_database
from visualizations import charts, theme
from services.circuit_service import CircuitService
from services.constructor_service import ConstructorService
from services.driver_service import DriverService
from services.prediction_service import PredictionService
from services.race_service import RaceService
from services.recommendation_service import RecommendationService


# ── Pure form calculator ─────────────────────────────────────────────
def test_rolling_average_ignores_dnf():
    assert form_calculator.rolling_average([2, None, 4], 3) == pytest.approx(3.0)
    assert form_calculator.rolling_average([None, None], 2) is None


def test_momentum_sign():
    # Improving (positions falling toward 1) -> positive momentum.
    assert form_calculator.momentum([10, 8, 6, 4, 2]) > 0
    # Declining -> negative.
    assert form_calculator.momentum([2, 4, 6, 8]) < 0


# ── Visualization theme ──────────────────────────────────────────────
def test_chart_applies_theme_without_registration():
    """Charts must render even when the named template was never registered.

    Regression: a Streamlit page opened directly does not run app.py, so the
    theme is applied as an object rather than by registered name.
    """
    fig = charts.bar_chart(["A", "B"], [1, 2])
    # The applied template is the PitWall object (carrying our dark background),
    # not a bare string name that would require prior registration.
    assert fig.layout.template.layout.paper_bgcolor == theme.BG_DARK


def test_streak_and_form_score():
    assert form_calculator.streak([True, False, True, True]) == 2
    assert form_calculator.form_score([1, 1, 1], window=3, field_size=20) == pytest.approx(
        100.0
    )
    assert form_calculator.dnf_rate([1, None, 3, None]) == pytest.approx(0.5)


# ── Seeded integration fixture ───────────────────────────────────────
@pytest.fixture()
def seeded_db(tmp_path: Path) -> Path:
    """Build a small, controlled dataset for service integration tests."""
    db = tmp_path / "seed.db"
    initialize_database(db)
    with get_connection(db) as conn:
        conn.executescript(
            """
            INSERT INTO circuits (id, name, country, circuit_type)
            VALUES (1, 'Monaco', 'Monaco', 'street'),
                   (2, 'Silverstone', 'UK', 'permanent');

            INSERT INTO drivers (id, code, first_name, last_name, full_name)
            VALUES (1, 'VER', 'Max', 'Verstappen', 'Max Verstappen'),
                   (2, 'NOR', 'Lando', 'Norris', 'Lando Norris');

            INSERT INTO constructors (id, name) VALUES (1, 'Red Bull'), (2, 'McLaren');

            INSERT INTO seasons (year, rounds) VALUES (2024, 2);

            INSERT INTO races (id, season, round, circuit_id, name, date)
            VALUES (1, 2024, 1, 1, 'Monaco GP', '2024-05-26'),
                   (2, 2024, 2, 2, 'British GP', '2024-07-07');

            -- Race 1: VER wins from pole, NOR 2nd.
            INSERT INTO results (race_id, driver_id, constructor_id, grid, position, points, status)
            VALUES (1, 1, 1, 1, 1, 25, 'Finished'),
                   (1, 2, 2, 3, 2, 18, 'Finished');
            -- Race 2: NOR wins, VER DNF.
            INSERT INTO results (race_id, driver_id, constructor_id, grid, position, points, status)
            VALUES (2, 2, 2, 1, 1, 25, 'Finished'),
                   (2, 1, 1, 2, NULL, 0, 'Engine');

            INSERT INTO qualifying (race_id, driver_id, constructor_id, position, q3_time_ms)
            VALUES (1, 1, 1, 1, 70000),
                   (1, 2, 2, 3, 70500),
                   (2, 2, 2, 1, 88000),
                   (2, 1, 1, 2, 88200);

            INSERT INTO pit_stops (race_id, driver_id, stop_number, lap, duration_ms)
            VALUES (1, 1, 1, 20, 2300), (2, 2, 1, 25, 2200);
            """
        )
    return db


def test_driver_service_profile(seeded_db: Path):
    svc = DriverService(db_path=seeded_db)
    assert len(svc.list_drivers()) == 2
    profile = svc.get_profile(1)
    assert profile["driver"]["code"] == "VER"
    assert profile["career"]["wins"] == 1
    assert profile["career"]["poles"] == 1
    assert profile["career"]["dnf_rate"] == pytest.approx(0.5)
    # Radar returns six normalised axes.
    radar = svc.radar_metrics(1)
    assert set(radar) == {
        "Qualifying", "Race Pace", "Consistency", "Overtaking",
        "Reliability", "Points Scoring",
    }
    assert all(0 <= v <= 100 for v in radar.values())


def test_driver_head_to_head(seeded_db: Path):
    svc = DriverService(db_path=seeded_db)
    h2h = svc.head_to_head(1, 2)
    # Only race 1 has both classified; VER beat NOR there.
    assert h2h["shared_races"] == 1
    assert h2h["driver_wins"] == 1
    assert h2h["other_wins"] == 0


def test_constructor_service(seeded_db: Path):
    svc = ConstructorService(db_path=seeded_db)
    profile = svc.get_profile(1, season=2024)
    assert profile["constructor"]["name"] == "Red Bull"
    # Red Bull: 1 finish out of 2 entries.
    assert profile["reliability"] == pytest.approx(0.5)
    assert profile["pit_stops"]["avg_ms"] == pytest.approx(2300.0)
    assert profile["season_form"]["wins"] == 1


def test_circuit_service(seeded_db: Path):
    svc = CircuitService(db_path=seeded_db)
    profile = svc.get_profile(1)
    assert profile["circuit"]["name"] == "Monaco"
    assert profile["characteristics"]["races"] == 1
    # Monaco race won from pole -> 100% conversion.
    assert profile["pole_conversion"] == pytest.approx(1.0)
    assert profile["top_drivers"][0]["code"] == "VER"


# ── Prediction + recommendation engine ───────────────────────────────
def test_prediction_service_predicts_field(model_db: Path):
    svc = PredictionService(db_path=model_db)
    result = svc.predict_race(12)
    ensemble = result["ensemble"]
    assert result["field_size"] == 5
    assert ensemble["probability"].sum() == pytest.approx(1.0, abs=1e-6)
    # Strongest driver (1) should be the model favourite.
    favourite = int(ensemble.sort_values("probability", ascending=False).iloc[0]["driver_id"])
    assert favourite == 1


def test_recommendation_engine_flags_value(model_db: Path):
    svc = RecommendationService(db_path=model_db)
    recs = svc.generate_for_race(12, market="race_winner")
    assert len(recs) == 5
    # Sorted by EV descending.
    evs = [r["expected_value"] for r in recs]
    assert evs == sorted(evs, reverse=True)
    top = recs[0]
    # Driver 1 is underpriced by the book (2.5 => 40% vs model ~75%): +EV value.
    assert top["driver_id"] == 1
    assert top["expected_value"] > 0
    assert top["edge_pct"] > 0
    assert 0 <= top["confidence"] <= 100
    assert top["verdict"] in {"STRONG_BET", "SMALL_EDGE"}
    assert "Model predicts" in top["explanation"]


def test_recommendations_persisted(model_db: Path):
    svc = RecommendationService(db_path=model_db)
    svc.generate_for_race(12)
    # Re-running must not duplicate rows for the race/market.
    svc.generate_for_race(12)
    from database.repositories.recommendations import RecommendationRepository

    repo = RecommendationRepository(db_path=model_db)
    assert len(repo.get_by_race(12)) == 5


def test_race_service(seeded_db: Path):
    svc = RaceService(db_path=seeded_db)
    assert svc.list_seasons() == [2024]
    assert len(svc.races_for_season(2024)) == 2
    latest = svc.latest_race()
    assert latest["name"] == "British GP"
    standings = svc.season_driver_standings(2024)
    # NOR: 18+25=43, VER: 25 -> NOR leads.
    assert standings[0]["code"] == "NOR"
    assert standings[0]["points"] == pytest.approx(43.0)
