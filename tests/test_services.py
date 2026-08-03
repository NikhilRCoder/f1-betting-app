"""Tests for the analysis + service layers against a seeded temporary database."""
from __future__ import annotations

from pathlib import Path

import pytest

from analysis import form_calculator
from database.connection import get_connection, initialize_database
from visualizations import charts, theme
from services.bet_service import BetService
from services.circuit_service import CircuitService
from services.constructor_service import ConstructorService
from services.driver_service import DriverService
from services.odds_service import OddsService
from services.prediction_service import PredictionService
from services.race_service import RaceService
from services.recommendation_service import RecommendationService
from services.report_service import ReportService


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


def test_build_calibrator(model_db: Path):
    svc = PredictionService(db_path=model_db)
    calibrator = svc.build_calibrator()
    # With the multi-season fixture there is enough OOS data to fit.
    assert calibrator.fitted
    # A calibrator file is written next to the db and re-loadable.
    from models.calibration import ProbabilityCalibrator

    reloaded = ProbabilityCalibrator.load(model_db.parent / "calibrator.json")
    assert reloaded.fitted
    # predict_race still returns a coherent distribution with calibration applied.
    ensemble = svc.predict_race(12)["ensemble"]
    assert ensemble["probability"].sum() == pytest.approx(1.0, abs=1e-6)


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


def test_predict_markets_and_h2h(model_db: Path):
    svc = PredictionService(db_path=model_db)
    out = svc.predict_markets(12)
    markets = out["markets"]
    assert set(markets) >= {"race_winner", "podium", "top5", "top10"}
    for name, df in markets.items():
        assert not df.empty
        # Ranked markets are per-driver probabilities in [0, 1].
        assert (df["probability"] >= 0).all() and (df["probability"] <= 1).all()
    # Podium prob for the field should exceed win prob on aggregate.
    assert markets["podium"]["probability"].sum() > markets["race_winner"]["probability"].sum()

    # Head-to-head is complementary and favours the stronger driver (id 1).
    h2h = svc.head_to_head(12, 1, 5)
    assert h2h["a_prob"] + h2h["b_prob"] == pytest.approx(1.0)
    assert h2h["a_prob"] > 0.5


def test_h2h_market_skipped_in_recommendations(model_db: Path):
    svc = RecommendationService(db_path=model_db)
    assert svc.generate_for_race(12, market="h2h") == []


def test_recommendations_persisted(model_db: Path):
    svc = RecommendationService(db_path=model_db)
    svc.generate_for_race(12)
    # Re-running must not duplicate rows for the race/market.
    svc.generate_for_race(12)
    from database.repositories.recommendations import RecommendationRepository

    repo = RecommendationRepository(db_path=model_db)
    assert len(repo.get_by_race(12)) == 5


# ── CSV import (Settings page backend) ───────────────────────────────
class _FakeUpload:
    """Minimal stand-in for a Streamlit UploadedFile."""

    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self._data = data

    def getbuffer(self) -> bytes:
        return self._data


def test_seed_from_uploaded(tmp_path: Path):
    from database.connection import initialize_database
    from database.repositories.drivers import DriverRepository
    from database.seed import seed_from_uploaded

    db = tmp_path / "up.db"
    initialize_database(db)
    files = [
        _FakeUpload(
            "drivers.csv",
            b"driverId,driverRef,code,forename,surname,dob,nationality\n"
            b"1,verstappen,VER,Max,Verstappen,1997-09-30,Dutch\n",
        ),
        _FakeUpload(
            "races.csv",
            b"raceId,year,round,circuitId,name,date,time\n"
            b"1,2024,1,1,Bahrain GP,2024-03-02,15:00:00\n",
        ),
        _FakeUpload(
            "circuits.csv",
            b"circuitId,circuitRef,name,location,country,lat,lng,alt\n"
            b"1,bahrain,Bahrain,Sakhir,Bahrain,26.0,50.5,7\n",
        ),
    ]
    counts = seed_from_uploaded(files, db_path=db, dest_dir=tmp_path / "csv")
    assert counts["drivers"] == 1
    assert counts["races"] == 1
    assert DriverRepository(db_path=db).get_by_code("VER")["last_name"] == "Verstappen"


def test_import_dataframe_matches_columns(tmp_path: Path):
    import pandas as pd

    from database.connection import initialize_database
    from database.repositories.drivers import DriverRepository
    from database.seed import import_dataframe

    db = tmp_path / "single.db"
    initialize_database(db)
    df = pd.DataFrame(
        [
            {"id": 7, "code": "HAM", "first_name": "Lewis", "last_name": "Hamilton",
             "full_name": "Lewis Hamilton", "ignored_col": "dropped"},
        ]
    )
    n = import_dataframe("drivers", df, db_path=db)
    assert n == 1
    rec = DriverRepository(db_path=db).get_by_id(7)
    assert rec["code"] == "HAM"
    # Unknown column must be ignored, not error.
    assert "ignored_col" not in rec


def test_import_dataframe_rejects_unknown_table(tmp_path: Path):
    import pandas as pd

    from database.connection import initialize_database
    from database.seed import import_dataframe

    db = tmp_path / "bad.db"
    initialize_database(db)
    with pytest.raises(ValueError):
        import_dataframe("not_a_table", pd.DataFrame([{"x": 1}]), db_path=db)


# ── Odds service ─────────────────────────────────────────────────────
def test_odds_resolve_and_manual(model_db: Path):
    svc = OddsService(db_path=model_db)
    # Code match.
    assert svc.resolve_driver("D1")["id"] == 1
    # Surname match ("L3" is driver 3's surname in the fixture).
    assert svc.resolve_driver("L3")["id"] == 3
    assert svc.resolve_driver("nobody") is None

    bet_id = svc.add_manual_odds(1, 1, "race_winner", "book", 4.0)
    assert bet_id > 0
    with pytest.raises(ValueError):
        svc.add_manual_odds(1, 1, "race_winner", "book", 0.9)


def test_odds_overround(model_db: Path):
    svc = OddsService(db_path=model_db)
    # Fixture seeded odds for race 12 (5 drivers).
    over = svc.market_overround(12, "race_winner")
    assert over is not None
    # Bookmaker book should carry a positive margin.
    assert over > 0


def test_odds_scrape_and_store_matches(model_db: Path, monkeypatch):
    svc = OddsService(db_path=model_db)
    html = (
        "<table><tr><th>Driver</th><th>Odds</th></tr>"
        "<tr><td>D1</td><td>2.0</td></tr>"
        "<tr><td>Nobody</td><td>3.0</td></tr></table>"
    )
    monkeypatch.setattr(svc._scraper, "fetch", lambda url: html)
    summary = svc.scrape_and_store("http://x", 1, "race_winner", "scraped")
    assert summary["stored"] == 1
    assert "Nobody" in summary["unmatched"]


# ── Bet service ──────────────────────────────────────────────────────
def test_bet_lifecycle_and_pnl(model_db: Path):
    svc = BetService(db_path=model_db)
    win = svc.place_bet(12, 1, "race_winner", 2.0, 100.0)
    loss = svc.place_bet(12, 2, "race_winner", 3.0, 50.0)
    assert svc.pnl_summary()["total_bets"] == 0  # nothing settled yet

    assert svc.settle_bet(win, "win") is True   # payout defaults to 200
    assert svc.settle_bet(loss, "loss") is True
    summary = svc.pnl_summary()
    assert summary["total_bets"] == 2
    assert summary["wins"] == 1
    # Profit: +100 (win) - 50 (loss) = 50 on 150 staked -> ROI 33.33%.
    assert summary["total_profit_loss"] == pytest.approx(50.0)
    assert summary["roi_pct"] == pytest.approx(33.33, abs=0.01)
    assert len(svc.pnl_timeline()) == 2


def test_bet_validation(model_db: Path):
    svc = BetService(db_path=model_db)
    with pytest.raises(ValueError):
        svc.place_bet(12, 1, "race_winner", 1.0, 10.0)
    with pytest.raises(ValueError):
        svc.place_bet(12, 1, "race_winner", 2.0, 0.0)


# ── Weekend pipeline & alerts ────────────────────────────────────────
def test_weekend_pipeline(model_db: Path):
    from services.pipeline_service import WeekendPipeline

    summary = WeekendPipeline(db_path=model_db).run(
        12, markets=("race_winner",), make_pdf=True
    )
    assert summary["race_id"] == 12
    assert "race_winner" in summary["counts"]
    assert summary["counts"]["race_winner"] == 5  # 5 priced drivers
    # The strongly-underpriced favourite should surface as a STRONG_BET.
    assert any(r["driver_id"] == 1 for r in summary["strong_bets"])
    assert summary["pdf_path"] and Path(summary["pdf_path"]).exists()
    Path(summary["pdf_path"]).unlink(missing_ok=True)
    # No SMTP configured in tests -> no alert sent.
    assert summary["alert_sent"] is False


def test_notify_no_op_when_unconfigured(monkeypatch):
    from utilities import notify

    for var in ("SMTP_HOST", "ALERT_EMAIL_TO", "SMTP_USER"):
        monkeypatch.delenv(var, raising=False)
    assert notify.is_configured() is False
    assert notify.send_email("subject", "body") is False


def test_notify_format_alert():
    from utilities import notify

    body = notify.format_alert(
        {"race_id": 1, "race_name": "Test GP", "strong_bets": [
            {"driver_id": 1, "driver": "Max", "market": "race_winner",
             "model_probability": 0.7, "implied_probability": 0.4,
             "expected_value": 0.75, "confidence": 80}
        ]}
    )
    assert "Test GP" in body and "STRONG_BET" in body and "Max" in body


# ── Report service ───────────────────────────────────────────────────
def test_report_exports(model_db: Path):
    rec = RecommendationService(db_path=model_db)
    rec.generate_for_race(12)
    svc = ReportService(db_path=model_db)

    csv_path = svc.export_recommendations_csv(12)
    xlsx_path = svc.export_recommendations_excel(12)
    pdf_path = svc.generate_prerace_pdf(12)
    try:
        assert csv_path.exists() and csv_path.stat().st_size > 0
        assert xlsx_path.exists() and xlsx_path.stat().st_size > 0
        assert pdf_path.exists() and pdf_path.stat().st_size > 0
    finally:
        for p in (csv_path, xlsx_path, pdf_path):
            p.unlink(missing_ok=True)


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
