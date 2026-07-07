"""Driver Analysis page.

Thin view. Will render career stats, form, circuit-type performance, qualifying
metrics, head-to-heads and a skill radar chart via ``driver_service``.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Driver Analysis", icon="👤")
coming_soon(
    phase="Phase 3",
    description=(
        "Career and season stats, current form, performance by circuit type, "
        "wet/night performance, qualifying analysis, DNF rates, teammate "
        "head-to-heads and a skill radar chart."
    ),
)
