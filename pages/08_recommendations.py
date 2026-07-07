"""Recommendations page — value-bet engine output.

Thin view. Will render the full recommendation table (edge, EV, Kelly,
confidence, verdict) with filtering and explanation via ``recommendation_service``.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Recommendations", icon="🎯")
coming_soon(
    phase="Phase 4 & 5",
    description=(
        "Full recommendation table with model vs implied probability, edge, EV, "
        "Kelly and confidence; verdict filtering, sorting, expandable "
        "explanations and comparison charts."
    ),
)
