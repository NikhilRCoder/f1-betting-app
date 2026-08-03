"""Recommendations page — value-bet engine output.

Thin view. Runs the recommendation engine for a selected race/market and renders
the ranked table, verdict filter, probability comparison and edge distribution.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from services.race_service import RaceService
from services.recommendation_service import RecommendationService
from utilities.ui import bootstrap_page
from visualizations import charts
from visualizations.theme import VERDICT_COLORS

bootstrap_page("Recommendations", icon="🎯")


@st.cache_resource
def _services() -> tuple[RaceService, RecommendationService]:
    return RaceService(), RecommendationService()


races_svc, rec_svc = _services()
seasons = races_svc.list_seasons()

if not seasons:
    st.info(
        "No data yet. Import races/results on **Settings** and add odds on the "
        "**Odds** page, then generate recommendations here."
    )
    st.stop()

col1, col2, col3 = st.columns(3)
season = col1.selectbox("Season", options=seasons)
races = races_svc.races_for_season(season)
race_names = {r["id"]: f"R{r['round']} — {r['name']}" for r in races}
race_id = col2.selectbox(
    "Race", options=list(race_names), format_func=lambda i: race_names[i]
)
market = col3.selectbox("Market", options=list(settings.MARKETS))

if market == "h2h":
    st.info(
        "Head-to-head is a pairwise market — use the **Upcoming Race** page's "
        "Head-to-head tool. Pick another market here for the ranked value table."
    )
    st.stop()

if st.button("Generate recommendations", type="primary"):
    with st.spinner("Training models and evaluating value…"):
        st.session_state["recs"] = rec_svc.generate_for_race(race_id, market=market)
        st.session_state["recs_key"] = (race_id, market)

recs = st.session_state.get("recs")
if not recs:
    st.caption(
        "Select a race with odds and click **Generate**. The engine trains on "
        "prior races, predicts this one, and compares against bookmaker odds."
    )
    st.stop()

df = pd.DataFrame(recs)

# ── Verdict filter ───────────────────────────────────────────────────
verdicts = st.multiselect(
    "Filter by verdict", options=list(settings.VERDICTS), default=list(settings.VERDICTS)
)
view = df[df["verdict"].isin(verdicts)]

# ── Summary tiles ────────────────────────────────────────────────────
counts = df["verdict"].value_counts().to_dict()
cols = st.columns(len(settings.VERDICTS))
for col, verdict in zip(cols, settings.VERDICTS):
    col.metric(verdict.replace("_", " "), counts.get(verdict, 0))

# ── Table ────────────────────────────────────────────────────────────
display_cols = [
    "driver_id", "model_probability", "implied_probability", "edge_pct",
    "expected_value", "kelly_fraction", "confidence", "verdict",
]
st.dataframe(
    view[display_cols].sort_values("expected_value", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# ── Charts ───────────────────────────────────────────────────────────
left, right = st.columns(2)
with left:
    st.markdown("#### Model vs bookmaker probability")
    st.plotly_chart(
        charts.probability_comparison(
            [str(d) for d in df["driver_id"]],
            df["model_probability"].tolist(),
            df["implied_probability"].tolist(),
        ),
        use_container_width=True,
    )
with right:
    st.markdown("#### Edge distribution")
    st.plotly_chart(
        charts.bar_chart(
            [str(d) for d in df["driver_id"]],
            df["edge_pct"].tolist(),
            y_title="Edge %",
        ),
        use_container_width=True,
    )

# ── Explanations ─────────────────────────────────────────────────────
st.markdown("#### Explanations")
for rec in sorted(recs, key=lambda r: r["expected_value"], reverse=True):
    color = VERDICT_COLORS.get(rec["verdict"], "#c8c8d4")
    with st.expander(
        f"Driver {rec['driver_id']} · {rec['verdict'].replace('_', ' ')} "
        f"· EV {rec['expected_value']:+.2%}"
    ):
        st.markdown(
            f"<span style='color:{color}'>**{rec['verdict'].replace('_', ' ')}**</span>",
            unsafe_allow_html=True,
        )
        st.write(rec["explanation"])
