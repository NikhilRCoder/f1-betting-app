"""Model Testing page — backtesting and comparison.

Thin view. Will run backtests over a season range, compare models on log-loss /
Brier / calibration and simulate P&L via ``prediction_service``.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Model Testing", icon="🧪")
coming_soon(
    phase="Phase 4",
    description=(
        "Model selection, season/race backtest range, accuracy metrics "
        "(log loss, Brier score), calibration plots, feature importance and a "
        "P&L simulation over historical recommendations."
    ),
)
