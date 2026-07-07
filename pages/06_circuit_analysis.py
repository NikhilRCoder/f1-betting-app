"""Circuit Analysis page.

Thin view. Will render physical stats, classification, historical race
characteristics and most-successful drivers/constructors via ``circuit_service``.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Circuit Analysis", icon="🛣️")
coming_soon(
    phase="Phase 3",
    description=(
        "Physical stats, street/permanent classification, historical overtakes "
        "and safety cars, pole-conversion rate, grid importance and the most "
        "successful drivers and constructors at the circuit."
    ),
)
