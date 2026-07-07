"""Constructor Analysis page.

Thin view. Will render team form, pit-stop performance, reliability, qualifying
pace and a track-type suitability heatmap via ``constructor_service``.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Constructor Analysis", icon="🏭")
coming_soon(
    phase="Phase 3",
    description=(
        "Current and historical form, pit-stop performance, reliability rate, "
        "qualifying pace, race pace vs field and a track-type suitability "
        "heatmap."
    ),
)
