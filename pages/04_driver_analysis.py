"""Driver Analysis page.

Thin view. Renders career stats, current form, qualifying metrics, circuit-type
splits, a skill radar and head-to-head — all sourced from ``DriverService``.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.driver_service import DriverService
from utilities.formatters import format_percentage
from utilities.ui import bootstrap_page
from visualizations import charts, radar

bootstrap_page("Driver Analysis", icon="👤")


@st.cache_resource
def _service() -> DriverService:
    return DriverService()


service = _service()
drivers = service.list_drivers()

if not drivers:
    st.info(
        "No drivers in the database yet. Import data on the **Settings** page "
        "(Phase 2 CSV seeding) to populate driver analysis."
    )
    st.stop()

names = {d["id"]: f"{d['full_name']} ({d['code']})" for d in drivers}
driver_id = st.selectbox(
    "Driver", options=list(names), format_func=lambda i: names[i]
)

profile = service.get_profile(driver_id)
career = profile["career"]
form = profile["form"]
qual = profile["qualifying"]

st.subheader(profile["driver"]["full_name"])

# ── Career headline stats ────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Starts", career["starts"])
c2.metric("Wins", career["wins"])
c3.metric("Podiums", career["podiums"])
c4.metric("Poles", career["poles"])
c5.metric("Points", career["total_points"])

c6, c7, c8 = st.columns(3)
c6.metric("Best finish", career["best_finish"] or "—")
c7.metric("DNF rate", format_percentage(career["dnf_rate"]))
c8.metric("Form score", f"{form['form_score']:.0f}/100")

# ── Form + radar ─────────────────────────────────────────────────────
left, right = st.columns(2)
with left:
    st.markdown("#### Recent form")
    positions = form["recent_positions"]
    if positions:
        fig = charts.line_chart(
            list(range(1, len(positions) + 1)),
            positions,
            title="Last races — finishing position",
            x_title="Race (oldest → newest)",
            y_title="Position",
        )
        fig.update_yaxes(autorange="reversed")  # P1 at the top
        st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Momentum: {form['momentum']:+.2f} · Points streak: {form['points_streak']}"
    )

with right:
    st.markdown("#### Skill profile")
    st.plotly_chart(
        radar.radar_chart(service.radar_metrics(driver_id), title=""),
        use_container_width=True,
    )

# ── Qualifying + circuit-type ────────────────────────────────────────
left, right = st.columns(2)
with left:
    st.markdown("#### Qualifying")
    st.write(
        {
            "Avg grid": qual["avg_position"],
            "Q3 rate": format_percentage(qual["q3_rate"]),
            "Pole rate": format_percentage(qual["pole_rate"]),
        }
    )
with right:
    st.markdown("#### Avg finish by circuit type")
    ct = profile["circuit_type"]
    if ct:
        st.plotly_chart(
            charts.bar_chart(
                list(ct.keys()), list(ct.values()), y_title="Avg finish"
            ),
            use_container_width=True,
        )
    else:
        st.caption("No classified results yet.")

# ── Recent results table ─────────────────────────────────────────────
st.markdown("#### Recent results")
recent = profile["recent_results"]
if recent:
    df = pd.DataFrame(recent)[["season", "round", "position", "points", "status"]]
    st.dataframe(df, use_container_width=True, hide_index=True)

# ── Head-to-head ─────────────────────────────────────────────────────
st.markdown("#### Head-to-head")
others = {i: n for i, n in names.items() if i != driver_id}
if others:
    other_id = st.selectbox(
        "Compare against", options=list(others), format_func=lambda i: others[i]
    )
    h2h = service.head_to_head(driver_id, other_id)
    a, b, c = st.columns(3)
    a.metric("Shared races", h2h["shared_races"])
    b.metric(f"{profile['driver']['code']} ahead", h2h["driver_wins"])
    c.metric(f"{names[other_id].split('(')[-1].rstrip(')')} ahead", h2h["other_wins"])
