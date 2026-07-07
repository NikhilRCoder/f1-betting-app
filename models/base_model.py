"""Abstract base for all prediction models.

Every model — Elo, logistic, XGBoost, Monte Carlo, ensemble — implements this
interface so models can be swapped, compared and ensembled without the service
layer knowing their internals.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd


class BaseModel(ABC):
    """Abstract base for all prediction models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique model identifier."""
        ...

    @abstractmethod
    def train(self, features: pd.DataFrame, target: pd.Series) -> None:
        """Train the model."""
        ...

    @abstractmethod
    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return DataFrame with columns: driver_id, probability."""
        ...

    @abstractmethod
    def evaluate(
        self, predictions: pd.DataFrame, actuals: pd.Series
    ) -> Dict[str, float]:
        """Return accuracy metrics: log_loss, brier_score, accuracy, etc."""
        ...

    def get_feature_importance(self) -> Dict[str, float]:
        """Optional: return feature importance scores."""
        return {}
