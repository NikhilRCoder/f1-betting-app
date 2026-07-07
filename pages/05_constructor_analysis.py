"""Constructor Analysis page.

Thin view. Renders reliability, pit-stop performance, season form and a
track-type suitability chart via ``ConstructorService``.
"""
from __future__ import annotations

import streamlit as st

from services.constructor_service import ConstructorService
from services.race_service import RaceService
from utilities.formatters import format_lap_time, format_percentage
from utilities.ui import bootstrap_page
from visualizations import charts

bootstrap_page("Constructor Analysis", icon="🏭")


@st.cache_resource
def _services() -> tuple[ConstructorService, RaceService]:
    return ConstructorService(), RaceService()


service, races = _services()
constructors = service.list_constructors()

if not constructors:
    st.info(
        "No constructors in the database yet. Import data on the **Settings** "
        "page to populate constructor analysis."
    )
    st.stop()

names = {c["id"]: c["name"] for c in constructors}
constructor_id = st.selectbox(
    "Constructor", options=list(names), format_func=lambda i: names[i]
)

seasons = races.list_seasons()
season = st.selectbox("Season", options=seasons) if seasons else None

profile = service.get_profile(constructor_id, season=season)

st.subheader(profile["constructor"]["name"])

# ── Headline ─────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Reliability", format_percentage(profile["reliability"]))
pit = profile["pit_stops"]
c2.metric("Avg pit stop", format_lap_time(pit["avg_ms"]) if pit["avg_ms"] else "—")
c3.metric("Best pit stop", format_lap_time(pit["best_ms"]) if pit["best_ms"] else "—")

if "season_form" in profile:
    sf = profile["season_form"]
    st.markdown(f"#### {season} season")
    a, b, c, d = st.columns(4)
    a.metric("Points", sf["points"])
    b.metric("Wins", sf["wins"])
    c.metric("Podiums", sf["podiums"])
    d.metric("Avg finish", sf["avg_finish"] or "—")

# ── Track type suitability ───────────────────────────────────────────
st.markdown("#### Avg finish by circuit type")
tt = profile["track_type"]
if tt:
    st.plotly_chart(
        charts.bar_chart(
            list(tt.keys()), list(tt.values()), y_title="Avg finish",
            color=None,
        ),
        use_container_width=True,
    )
else:
    st.caption("No classified results yet.")
