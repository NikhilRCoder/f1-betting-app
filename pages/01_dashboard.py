"""Dashboard page — home / overview.

Thin view. Will surface latest results, the upcoming-race card, quick P&L stats,
top recommendations and model-confidence gauges via the service layer.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Dashboard", icon="📊")
coming_soon(
    phase="Phase 3 & 5",
    description=(
        "Latest race summary, upcoming-race card, quick stats "
        "(bets, ROI, yield, bankroll), top-3 recommendations, confidence "
        "gauges and a recent P&L chart."
    ),
)
