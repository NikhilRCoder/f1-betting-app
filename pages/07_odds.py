"""Odds page — scraping and management.

Thin view. Will provide URL scraping, manual entry, a sortable odds table,
bookmaker comparison and an overround calculator via ``odds_service``.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Odds", icon="💱")
coming_soon(
    phase="Phase 5",
    description=(
        "URL scraping into the database, manual odds entry, a sortable/"
        "filterable odds table, cross-bookmaker comparison, implied "
        "probabilities and an overround calculator."
    ),
)
