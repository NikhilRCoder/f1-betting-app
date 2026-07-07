"""Historical Analysis page.

Thin view. Will let the user explore past seasons, races and results with charts
sourced from the analysis + service layers.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Historical Analysis", icon="📜")
coming_soon(
    phase="Phase 3",
    description=(
        "Season and race browsing, results tables, and trend charts across "
        "historical Formula One data."
    ),
)
