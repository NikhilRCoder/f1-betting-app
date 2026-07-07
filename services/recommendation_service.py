"""Recommendation service — the value-detection engine.

For every driver in a market it compares the model probability against the
bookmaker's implied probability, computes edge, expected value, a Kelly fraction
and a 0-100 confidence score, then assigns a verdict and a human-readable
explanation. Results are persisted to ``recommendations``.

This is the heart of the platform: turning probabilities and prices into
actionable, bankroll-aware betting decisions.
"""
from __future__ import annotations

from pathlib import Path
from statistics import pstdev
from typing import Any

import pandas as pd

from analysis.constructor_analysis import ConstructorAnalyzer
from analysis.driver_analysis import DriverAnalyzer
from calculators import expected_value, kelly, probability
from config import settings
from config.logging_config import get_logger
from database.repositories.odds import OddsRepository
from database.repositories.races import RaceRepository
from database.repositories.recommendations import RecommendationRepository
from database.repositories.results import ResultRepository
from services.prediction_service import PredictionService
from utilities.formatters import format_percentage, format_signed_percentage
from utilities.helpers import clamp, safe_div

logger = get_logger(__name__)

# Confidence component weights (must sum to 1.0). Mirrors the build spec.
_CONFIDENCE_WEIGHTS = {
    "sample_size": 0.15,
    "model_agreement": 0.25,
    "driver_form": 0.15,
    "constructor_form": 0.15,
    "track_familiarity": 0.10,
    "weather_certainty": 0.10,
    "edge_magnitude": 0.10,
}
# No per-session weather-forecast volatility yet: use a neutral certainty.
_NEUTRAL_WEATHER = 60.0


class RecommendationService:
    """Generate, score and persist betting recommendations for a race."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path
        self._predictions = PredictionService(db_path=db_path)
        self._odds = OddsRepository(db_path=db_path)
        self._recommendations = RecommendationRepository(db_path=db_path)
        self._races = RaceRepository(db_path=db_path)
        self._results = ResultRepository(db_path=db_path)
        self._driver = DriverAnalyzer(db_path=db_path)
        self._constructor = ConstructorAnalyzer(db_path=db_path)

    def generate_for_race(
        self,
        race_id: int,
        market: str = "race_winner",
        kelly_fraction: float = settings.DEFAULT_KELLY_FRACTION,
    ) -> list[dict[str, Any]]:
        """Produce and persist recommendations for a race/market.

        Args:
            race_id: Target race primary-key id.
            market: Betting market (must be a recognised market).
            kelly_fraction: Fractional-Kelly multiplier for stake sizing.

        Returns:
            A list of recommendation dicts sorted by expected value (desc).
        """
        prediction = self._predictions.predict_race(race_id, market=market)
        ensemble = prediction["ensemble"]
        if ensemble is None or ensemble.empty:
            logger.info("No predictions available for race %s.", race_id)
            return []

        race = self._races.get_by_id(race_id)
        circuit_id = race["circuit_id"] if race else None
        model_prob = {int(r["driver_id"]): float(r["probability"]) for _, r in ensemble.iterrows()}
        per_model = prediction["per_model"]

        recommendations: list[dict[str, Any]] = []
        self._recommendations.query(
            "DELETE FROM recommendations WHERE race_id = ? AND market = ?",
            (race_id, market),
        )

        for driver_id, m_prob in model_prob.items():
            odds_row = self._odds.get_latest_for_driver(race_id, driver_id, market)
            if odds_row is None:
                continue
            decimal_odds = odds_row["odds_decimal"]
            implied = probability.decimal_to_implied(decimal_odds)
            edge = m_prob - implied
            ev = expected_value.calculate_ev(m_prob, decimal_odds)
            kelly_frac = kelly.fractional_kelly(m_prob, decimal_odds, kelly_fraction)
            confidence = self._confidence(
                driver_id, circuit_id, m_prob, edge, per_model
            )
            verdict = self._verdict(ev, confidence)
            explanation = self._explain(
                driver_id, m_prob, implied, edge, confidence, verdict
            )
            rec = {
                "race_id": race_id,
                "driver_id": driver_id,
                "market": market,
                "model_probability": round(m_prob, 6),
                "implied_probability": round(implied, 6),
                "expected_value": round(ev, 6),
                "edge_pct": round(edge * 100, 4),
                "kelly_fraction": round(kelly_frac, 6),
                "confidence": round(confidence, 1),
                "verdict": verdict,
                "explanation": explanation,
            }
            self._recommendations.insert(rec)
            recommendations.append(rec)

        recommendations.sort(key=lambda r: r["expected_value"], reverse=True)
        logger.info(
            "Generated %d recommendations for race %s (%s).",
            len(recommendations), race_id, market,
        )
        return recommendations

    # ── Confidence ───────────────────────────────────────────────────
    def _confidence(
        self,
        driver_id: int,
        circuit_id: int | None,
        model_prob: float,
        edge: float,
        per_model: dict[str, pd.DataFrame],
    ) -> float:
        """Return a 0-100 confidence score from weighted components."""
        components = {
            "sample_size": self._sample_size_score(driver_id, circuit_id),
            "model_agreement": self._agreement_score(driver_id, per_model),
            "driver_form": self._driver_form_score(driver_id),
            "constructor_form": self._constructor_form_score(driver_id),
            "track_familiarity": self._track_familiarity_score(driver_id, circuit_id),
            "weather_certainty": _NEUTRAL_WEATHER,
            "edge_magnitude": clamp(edge / 0.20 * 100.0, 0.0, 100.0),
        }
        score = sum(_CONFIDENCE_WEIGHTS[k] * v for k, v in components.items())
        return clamp(score, 0.0, 100.0)

    def _sample_size_score(self, driver_id: int, circuit_id: int | None) -> float:
        """Score based on career starts (saturating at ~60 starts)."""
        starts = len(self._results.get_by_driver(driver_id))
        return clamp(starts / 60.0 * 100.0, 0.0, 100.0)

    def _agreement_score(
        self, driver_id: int, per_model: dict[str, pd.DataFrame]
    ) -> float:
        """Score model agreement: lower dispersion of member probabilities = higher."""
        probs = []
        for name, df in per_model.items():
            if name == "ensemble":
                continue
            match = df[df["driver_id"] == driver_id]
            if not match.empty:
                probs.append(float(match["probability"].iloc[0]))
        if len(probs) < 2:
            return 50.0
        # Normalise dispersion by the mean so agreement is scale-aware.
        dispersion = safe_div(pstdev(probs), max(sum(probs) / len(probs), 1e-6))
        return clamp((1.0 - min(dispersion, 1.0)) * 100.0, 0.0, 100.0)

    def _driver_form_score(self, driver_id: int) -> float:
        """Recent driver form as a 0-100 score."""
        return clamp(self._driver.current_form(driver_id)["form_score"], 0.0, 100.0)

    def _constructor_form_score(self, driver_id: int) -> float:
        """Constructor reliability (proxy for team form) as a 0-100 score."""
        recent = self._results.get_by_driver(driver_id, limit=1)
        if not recent:
            return 50.0
        constructor_id = recent[0]["constructor_id"]
        return clamp(self._constructor.reliability_rate(constructor_id) * 100.0, 0.0, 100.0)

    def _track_familiarity_score(self, driver_id: int, circuit_id: int | None) -> float:
        """Score based on how often the driver has raced at the circuit."""
        if circuit_id is None:
            return 50.0
        appearances = len(self._results.get_by_driver_at_circuit(driver_id, circuit_id))
        return clamp(appearances / 8.0 * 100.0, 0.0, 100.0)

    # ── Verdict & explanation ────────────────────────────────────────
    @staticmethod
    def _verdict(ev: float, confidence: float) -> str:
        """Assign a verdict from expected value and confidence."""
        if ev > settings.STRONG_BET_EV and confidence > settings.STRONG_BET_CONFIDENCE:
            return "STRONG_BET"
        if ev > settings.SMALL_EDGE_EV and confidence > settings.SMALL_EDGE_CONFIDENCE:
            return "SMALL_EDGE"
        if ev < settings.AVOID_EV:
            return "AVOID"
        return "NO_BET"

    def _explain(
        self,
        driver_id: int,
        model_prob: float,
        implied: float,
        edge: float,
        confidence: float,
        verdict: str,
    ) -> str:
        """Build a human-readable explanation string for a recommendation."""
        driver = self._results.query(
            "SELECT full_name FROM drivers WHERE id = ?", (driver_id,)
        )
        name = driver[0]["full_name"] if driver else f"Driver {driver_id}"
        edge_word = "value" if edge > 0 else "overpriced"
        return (
            f"Model predicts {name} at {format_percentage(model_prob)}. "
            f"Bookmaker implied probability is {format_percentage(implied)}. "
            f"Edge: {format_signed_percentage(edge)} ({edge_word}). "
            f"Confidence: {confidence:.0f}/100. Recommendation: {verdict.replace('_', ' ')}."
        )
