"""Tests for the prediction models."""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from models.base_model import BaseModel
from models.bayesian_model import BayesianModel
from models.elo_model import EloModel
from models.ensemble import EnsembleModel
from models.feature_engineering import TARGET_COLUMN, FeatureEngineer
from models.logistic_model import LogisticModel
from models.monte_carlo import MonteCarloModel, simulate_markets
from models.power_ratings import PowerRatingsModel
from models.xgboost_model import XGBoostModel


def test_base_model_is_abstract():
    assert inspect.isabstract(BaseModel)


def _split(model_db: Path):
    """Return (history, target, last_race_features) from the shared fixture."""
    fe = FeatureEngineer(db_path=model_db)
    matrix = fe.build_matrix()
    target_date = matrix[matrix["race_id"] == 12]["date"].iloc[0]
    history = matrix[matrix["date"] < target_date]
    race = matrix[matrix["race_id"] == 12]
    return history, history[TARGET_COLUMN], race


ALWAYS_ON = [EloModel, PowerRatingsModel, BayesianModel, MonteCarloModel]


@pytest.mark.parametrize("model_cls", ALWAYS_ON)
def test_pure_models_train_predict(model_cls, model_db: Path):
    history, target, race = _split(model_db)
    model = model_cls()
    model.train(history, target)
    preds = model.predict(race)
    assert list(preds.columns) == ["driver_id", "probability"]
    assert preds["probability"].sum() == pytest.approx(1.0, abs=1e-6)
    assert (preds["probability"] >= 0).all()


def test_ml_models_train_predict(model_db: Path):
    history, target, race = _split(model_db)
    for model in (LogisticModel(), XGBoostModel()):
        if not model.is_available():
            pytest.skip(f"{model.name} dependency not installed")
        model.train(history, target)
        preds = model.predict(race)
        assert preds["probability"].sum() == pytest.approx(1.0, abs=1e-6)


def test_elo_rates_stronger_driver_higher(model_db: Path):
    history, target, race = _split(model_db)
    elo = EloModel()
    elo.train(history, target)
    ratings = elo.ratings
    # Driver 1 is the strongest in the fixture; should out-rate driver 5.
    assert ratings[1] > ratings[5]


def test_evaluate_returns_metrics(model_db: Path):
    history, target, race = _split(model_db)
    model = PowerRatingsModel()
    model.train(history, target)
    preds = model.predict(race)
    actuals = race[TARGET_COLUMN].reset_index(drop=True)
    metrics = model.evaluate(preds.reset_index(drop=True), actuals)
    assert set(metrics) == {"log_loss", "brier_score", "accuracy"}


def test_ensemble_weights_and_predict(model_db: Path):
    history, target, race = _split(model_db)
    members = [EloModel(), PowerRatingsModel(), BayesianModel()]
    ensemble = EnsembleModel(members)
    ensemble.train(history, target)
    assert ensemble.weights == pytest.approx(
        {"elo": 1 / 3, "power_ratings": 1 / 3, "bayesian": 1 / 3}
    )
    preds = ensemble.predict(race)
    assert preds["probability"].sum() == pytest.approx(1.0, abs=1e-6)


def test_ensemble_requires_members():
    with pytest.raises(ValueError):
        EnsembleModel([])


def test_monte_carlo_markets_are_ordered():
    # Stronger driver should have higher win/podium probabilities.
    markets = simulate_markets({1: 5.0, 2: 3.0, 3: 1.0}, n_sims=20_000, seed=7)
    assert markets[1]["race_winner"] > markets[3]["race_winner"]
    # Podium prob >= win prob for any driver.
    for d in markets:
        assert markets[d]["podium"] >= markets[d]["race_winner"] - 1e-9
