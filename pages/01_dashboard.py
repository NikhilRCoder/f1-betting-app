"""Dashboard page — home / overview.

Thin view. Surfaces the latest race result, season standings and data coverage.
P&L, recommendations and confidence gauges are layered on in Phases 4–5.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.race_service import RaceService
from utilities.ui import bootstrap_page

bootstrap_page("Dashboard", icon="📊")


@st.cache_resource
def _service() -> RaceService:
    return RaceService()


service = _service()
seasons = service.list_seasons()

if not seasons:
    st.info(
        "Welcome to **PitWall**. The database is empty — head to the "
        "**Settings** page to import Ergast CSV data, then return here for the "
        "overview."
    )
    st.stop()

# ── Latest race ──────────────────────────────────────────────────────
latest = service.latest_race()
if latest:
    st.markdown(f"#### Latest race — {latest['name']} ({latest['season']})")
    st.caption(f"{latest['circuit_name']}, {latest['country']} · {latest['date']}")
    results = service.race_results(latest["id"])
    podium = [r for r in results if r["position"] in (1, 2, 3)]
    if podium:
        cols = st.columns(3)
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for col, row in zip(cols, podium):
            col.metric(
                f"{medals.get(row['position'], '')} P{row['position']}",
                row["code"] or row["driver"],
                row["constructor"],
            )

# ── Season snapshot ──────────────────────────────────────────────────
latest_season = seasons[0]
st.markdown(f"#### {latest_season} championship leaders")
standings = service.season_driver_standings(latest_season)
if standings:
    st.dataframe(
        pd.DataFrame(standings).head(5), use_container_width=True, hide_index=True
    )

# ── Coverage ─────────────────────────────────────────────────────────
st.divider()
st.markdown("#### Data coverage")
c1, c2 = st.columns(2)
c1.metric("Seasons", len(seasons))
c2.metric("Range", f"{min(seasons)}–{max(seasons)}")
st.caption(
    "P&L tracking, model predictions and value recommendations arrive in "
    "Phases 4–5."
)
