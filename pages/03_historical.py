"""Historical Analysis page.

Thin view. Browse past seasons, race calendars, race results and season driver
standings via ``RaceService``.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.race_service import RaceService
from utilities.ui import bootstrap_page
from visualizations import charts

bootstrap_page("Historical Analysis", icon="📜")


@st.cache_resource
def _service() -> RaceService:
    return RaceService()


service = _service()
seasons = service.list_seasons()

if not seasons:
    st.info(
        "No seasons in the database yet. Import data on the **Settings** page "
        "to explore historical results."
    )
    st.stop()

season = st.selectbox("Season", options=seasons)

# ── Season standings ─────────────────────────────────────────────────
st.markdown("#### Driver standings")
standings = service.season_driver_standings(season)
if standings:
    df = pd.DataFrame(standings)
    st.plotly_chart(
        charts.bar_chart(
            df["code"].tolist(),
            df["points"].tolist(),
            title=f"{season} points",
            y_title="Points",
        ),
        use_container_width=True,
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

# ── Race browser ─────────────────────────────────────────────────────
st.markdown("#### Races")
races = service.races_for_season(season)
if races:
    race_names = {r["id"]: f"R{r['round']} — {r['name']}" for r in races}
    race_id = st.selectbox(
        "Race", options=list(race_names), format_func=lambda i: race_names[i]
    )
    results = service.race_results(race_id)
    if results:
        st.dataframe(
            pd.DataFrame(results), use_container_width=True, hide_index=True
        )
    else:
        st.caption("No results recorded for this race.")
