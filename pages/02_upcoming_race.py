"""Upcoming Race page — race deep-dive.

Thin view. Will integrate circuit profile, weather, historical stats, current
odds, model probabilities and value-highlighted recommendation cards.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Upcoming Race", icon="🏁")
coming_soon(
    phase="Phase 5",
    description=(
        "Race selector, circuit profile, weather forecast, historical winners "
        "and podiums, safety-car/DNF stats, current odds, model predictions "
        "and recommendation cards with explanations."
    ),
)
