"""Prediction service — run models and persist predictions.

Builds the leak-free feature matrix, trains the available models on history
*before* a target race, predicts that race and stores the results in
``model_predictions``. Models that require an unavailable dependency (e.g.
XGBoost) are skipped gracefully.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from config.logging_config import get_logger
from database.repositories.predictions import PredictionRepository
from database.repositories.races import RaceRepository
from models.base_model import BaseModel
from models.bayesian_model import BayesianModel
from models.elo_model import EloModel
from models.ensemble import EnsembleModel
from models.feature_engineering import TARGET_COLUMN, FeatureEngineer
from models.logistic_model import LogisticModel
from models.monte_carlo import MonteCarloModel
from models.power_ratings import PowerRatingsModel
from models.xgboost_model import XGBoostModel
from utilities.helpers import to_json

logger = get_logger(__name__)


def _metrics_from_pairs(pairs: list[tuple[float, float]]) -> dict[str, float]:
    """Compute log-loss, Brier score and accuracy from (prob, actual) pairs."""
    import numpy as np

    if not pairs:
        return {"log_loss": 0.0, "brier_score": 0.0, "accuracy": 0.0}
    p = np.clip(np.array([x[0] for x in pairs]), 1e-9, 1 - 1e-9)
    y = np.array([x[1] for x in pairs])
    log_loss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    brier = float(np.mean((p - y) ** 2))
    accuracy = float(np.mean((p >= 0.5) == (y >= 0.5)))
    return {
        "log_loss": round(log_loss, 4),
        "brier_score": round(brier, 4),
        "accuracy": round(accuracy, 4),
    }


def _calibration_from_pairs(
    pairs: list[tuple[float, float]], bins: int = 10
) -> list[dict[str, float]]:
    """Return calibration points: mean predicted vs observed frequency per bin."""
    import numpy as np

    if not pairs:
        return []
    p = np.array([x[0] for x in pairs])
    y = np.array([x[1] for x in pairs])
    edges = np.linspace(0, 1, bins + 1)
    points = []
    for i in range(bins):
        mask = (p >= edges[i]) & (p < edges[i + 1])
        if mask.sum() == 0:
            continue
        points.append(
            {
                "predicted": round(float(p[mask].mean()), 4),
                "observed": round(float(y[mask].mean()), 4),
                "count": int(mask.sum()),
            }
        )
    return points


def build_default_models() -> list[BaseModel]:
    """Return the default set of models, skipping unavailable dependencies."""
    models: list[BaseModel] = [
        EloModel(),
        PowerRatingsModel(),
        BayesianModel(),
        MonteCarloModel(n_sims=5_000),
    ]
    if LogisticModel.is_available():
        models.append(LogisticModel())
    if XGBoostModel.is_available():
        models.append(XGBoostModel())
    return models


class PredictionService:
    """Train models and produce/persist per-race win predictions."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path
        self._features = FeatureEngineer(db_path=db_path)
        self._predictions = PredictionRepository(db_path=db_path)
        self._races = RaceRepository(db_path=db_path)

    def predict_race(
        self, race_id: int, market: str = "race_winner"
    ) -> dict[str, Any]:
        """Train on prior races and predict ``race_id``.

        Args:
            race_id: Target race primary-key id.
            market: Market label to tag predictions with (win market only for
                the ML models; Monte Carlo exposes multi-market separately).

        Returns:
            A dict with ``ensemble`` (DataFrame), ``per_model`` (name → DataFrame)
            and ``field_size``. Empty ``ensemble`` when there is no data.
        """
        matrix = self._features.build_matrix()
        if matrix.empty:
            return {"ensemble": pd.DataFrame(), "per_model": {}, "field_size": 0}

        race = self._races.get_by_id(race_id)
        if race is None:
            raise ValueError(f"Unknown race id {race_id}.")

        race_rows = matrix[matrix["race_id"] == race_id]
        if race_rows.empty:
            return {"ensemble": pd.DataFrame(), "per_model": {}, "field_size": 0}

        # Leak-free training set: everything strictly before this race's date.
        target_date = race_rows["date"].iloc[0]
        history = matrix[matrix["date"] < target_date]
        models = build_default_models()
        trained = self._train_models(models, history)

        ensemble = EnsembleModel(trained) if trained else None
        per_model: dict[str, pd.DataFrame] = {}
        for model in trained:
            per_model[model.name] = model.predict(race_rows)

        ensemble_pred = (
            ensemble.predict(race_rows) if ensemble else pd.DataFrame()
        )
        if ensemble is not None:
            per_model["ensemble"] = ensemble_pred

        self._persist(race_id, market, per_model)
        return {
            "ensemble": ensemble_pred,
            "per_model": per_model,
            "field_size": len(race_rows),
        }

    def backtest(
        self, season: int, model_names: list[str] | None = None
    ) -> dict[str, Any]:
        """Backtest models over a season, retraining before each race.

        For every race in ``season`` the models are trained on all races that
        occurred earlier, then used to predict that race. Predicted win
        probabilities are collected against actual outcomes to compute aggregate
        metrics and a calibration curve — with no look-ahead bias.

        Args:
            season: Season to backtest.
            model_names: Optional subset of model names to evaluate.

        Returns:
            A dict with ``metrics`` (per model), ``calibration`` (per model),
            ``feature_importance`` (per model) and ``n_races``.
        """
        matrix = self._features.build_matrix()
        if matrix.empty:
            return {"metrics": {}, "calibration": {}, "feature_importance": {}, "n_races": 0}

        season_races = (
            matrix[matrix["season"] == season]["race_id"].drop_duplicates().tolist()
        )
        collected: dict[str, list[tuple[float, float]]] = {}
        importance: dict[str, dict[str, float]] = {}
        n_races = 0

        for race_id in season_races:
            race_rows = matrix[matrix["race_id"] == race_id]
            target_date = race_rows["date"].iloc[0]
            history = matrix[matrix["date"] < target_date]
            if history.empty or history[TARGET_COLUMN].nunique() < 2:
                continue
            n_races += 1
            models = build_default_models()
            if model_names:
                models = [m for m in models if m.name in model_names]
            trained = self._train_models(models, history)
            for model in trained:
                preds = model.predict(race_rows).set_index("driver_id")["probability"]
                actual = race_rows.set_index("driver_id")[TARGET_COLUMN]
                pairs = collected.setdefault(model.name, [])
                for did, prob in preds.items():
                    pairs.append((float(prob), float(actual.loc[did])))
                importance[model.name] = model.get_feature_importance()

        metrics = {
            name: _metrics_from_pairs(pairs) for name, pairs in collected.items()
        }
        calibration = {
            name: _calibration_from_pairs(pairs) for name, pairs in collected.items()
        }
        return {
            "metrics": metrics,
            "calibration": calibration,
            "feature_importance": importance,
            "n_races": n_races,
        }

    def _train_models(
        self, models: list[BaseModel], history: pd.DataFrame
    ) -> list[BaseModel]:
        """Train each model on history, dropping any that fail to train."""
        target = history[TARGET_COLUMN] if not history.empty else pd.Series(dtype=int)
        trained: list[BaseModel] = []
        for model in models:
            try:
                model.train(history, target)
                trained.append(model)
            except (RuntimeError, ValueError) as exc:
                logger.warning("Skipping model %s: %s", model.name, exc)
        return trained

    def _persist(
        self, race_id: int, market: str, per_model: dict[str, pd.DataFrame]
    ) -> None:
        """Replace and store predictions for each model in the database."""
        for model_name, preds in per_model.items():
            if preds.empty:
                continue
            self._predictions.delete_for_race_model(race_id, model_name)
            records = [
                {
                    "race_id": race_id,
                    "driver_id": int(row["driver_id"]),
                    "model_name": model_name,
                    "market": market,
                    "probability": float(row["probability"]),
                    "confidence": None,
                    "features_used": to_json({"market": market}),
                }
                for _, row in preds.iterrows()
            ]
            self._predictions.insert_many(records)
        logger.info("Persisted predictions for race %s (%d models)", race_id, len(per_model))
