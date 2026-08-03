"""Upcoming Race page — race deep-dive.

Thin view. Integrates the circuit profile, current odds, model predictions and
value-highlighted recommendation cards for a selected race.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from database.repositories.drivers import DriverRepository
from services.circuit_service import CircuitService
from services.odds_service import OddsService
from services.pipeline_service import WeekendPipeline
from services.prediction_service import PredictionService
from services.race_service import RaceService
from services.recommendation_service import RecommendationService
from utilities.formatters import format_percentage, format_signed_percentage
from utilities.ui import bootstrap_page
from visualizations import charts
from visualizations.theme import VERDICT_COLORS

bootstrap_page("Upcoming Race", icon="🏁")


@st.cache_resource
def _services():
    return (
        RaceService(),
        CircuitService(),
        OddsService(),
        RecommendationService(),
        PredictionService(),
        DriverRepository(),
        WeekendPipeline(),
    )


(
    races_svc, circuit_svc, odds_svc, rec_svc, pred_svc, drivers_repo, pipeline
) = _services()
seasons = races_svc.list_seasons()

if not seasons:
    st.info("No races yet. Import data on the **Settings** page first.")
    st.stop()

col1, col2 = st.columns(2)
season = col1.selectbox("Season", options=seasons)
races = races_svc.races_for_season(season)
race_names = {r["id"]: f"R{r['round']} — {r['name']}" for r in races}
race_id = col2.selectbox("Race", options=list(race_names), format_func=lambda i: race_names[i])

race = next(r for r in races if r["id"] == race_id)
st.subheader(f"{race['name']} ({season})")
st.caption(f"{race['circuit_name']}, {race['country']} · {race['date']}")

# ── Circuit profile ──────────────────────────────────────────────────
profile = circuit_svc.get_profile(race["circuit_id"])
circuit = profile["circuit"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Type", circuit.get("circuit_type") or "—")
c2.metric("Length (km)", circuit.get("length_km") or "—")
c3.metric("Corners", circuit.get("corners") or "—")
gi = profile["grid_importance"]
c4.metric("Grid→finish corr", gi if gi is not None else "—")

# ── Odds snapshot ────────────────────────────────────────────────────
st.markdown("#### Current odds — race winner")
odds_rows = odds_svc.get_market_table(race_id, "race_winner")
if odds_rows:
    odf = pd.DataFrame(odds_rows)[["driver", "code", "bookmaker", "odds_decimal"]]
    st.dataframe(odf, use_container_width=True, hide_index=True)
    overround = odds_svc.market_overround(race_id, "race_winner")
    if overround is not None:
        st.caption(f"Overround: {format_signed_percentage(overround)}")
else:
    st.caption("No odds recorded yet — add them on the **Odds** page.")

# ── Predictions + recommendations ────────────────────────────────────
st.markdown("#### Model view & value")
if st.button("Run model & find value", type="primary"):
    with st.spinner("Training models and evaluating value…"):
        st.session_state["ur_recs"] = rec_svc.generate_for_race(race_id, "race_winner")

recs = st.session_state.get("ur_recs")
if recs:
    df = pd.DataFrame(recs)
    st.plotly_chart(
        charts.probability_comparison(
            [str(d) for d in df["driver_id"]],
            df["model_probability"].tolist(),
            df["implied_probability"].tolist(),
            title="Model vs bookmaker",
        ),
        use_container_width=True,
    )
    st.markdown("##### Value bets")
    value = [r for r in recs if r["verdict"] in ("STRONG_BET", "SMALL_EDGE")]
    if not value:
        st.caption("No positive-value bets detected for this market.")
    for rec in value:
        color = VERDICT_COLORS.get(rec["verdict"], "#c8c8d4")
        st.markdown(
            f"<div style='border-left:4px solid {color};padding-left:10px;margin:6px 0'>"
            f"<b>Driver {rec['driver_id']}</b> — {rec['verdict'].replace('_', ' ')}<br>"
            f"Model {format_percentage(rec['model_probability'])} vs implied "
            f"{format_percentage(rec['implied_probability'])} · "
            f"EV {rec['expected_value']:+.1%} · Conf {rec['confidence']:.0f}/100"
            f"</div>",
            unsafe_allow_html=True,
        )
elif recs is not None:
    st.caption("No recommendations (no odds for this race yet).")
else:
    st.caption("Click above to run the models and detect value against the odds.")

# ── Race weekend pipeline ────────────────────────────────────────────
st.markdown("#### Race weekend")
st.caption(
    "One click: evaluate value across win / podium / top-5 / top-10, flag "
    "STRONG_BETs and generate the pre-race PDF."
)
if st.button("Run full weekend"):
    with st.spinner("Running models across all markets…"):
        st.session_state["ur_weekend"] = pipeline.run(race_id, make_pdf=True)

wk = st.session_state.get("ur_weekend")
if wk and st.session_state.get("ur_weekend", {}).get("race_id") == race_id:
    strong = wk["strong_bets"]
    if strong:
        st.success(f"🔔 {len(strong)} STRONG_BET opportunity(ies) detected.")
        for r in strong:
            st.markdown(
                f"- **Driver {r['driver_id']}** [{r['market']}] — "
                f"model {format_percentage(r['model_probability'])} vs implied "
                f"{format_percentage(r['implied_probability'])} · "
                f"EV {r['expected_value']:+.1%} · conf {r['confidence']:.0f}/100"
            )
    else:
        st.info("No STRONG_BET opportunities across the evaluated markets.")
    cts = ", ".join(f"{m}: {n}" for m, n in wk["counts"].items())
    st.caption(f"Recommendations generated — {cts}.")
    if wk["pdf_path"]:
        with open(wk["pdf_path"], "rb") as fh:
            st.download_button(
                "Download pre-race PDF", data=fh.read(),
                file_name=wk["pdf_path"].split("/")[-1], mime="application/pdf",
            )

# ── Head-to-head ─────────────────────────────────────────────────────
st.markdown("#### Head-to-head")
st.caption(
    "Model probability that one driver finishes ahead of another "
    "(Plackett–Luce over the ensemble)."
)
field = drivers_repo.query(
    """
    SELECT DISTINCT d.id, d.full_name, d.code
    FROM results res JOIN drivers d ON d.id = res.driver_id
    WHERE res.race_id = ?
    ORDER BY d.last_name
    """,
    (race_id,),
)
if len(field) < 2:
    st.caption("Not enough drivers with data for this race to compare.")
else:
    names = {d["id"]: f"{d['full_name']} ({d['code']})" for d in field}
    hc1, hc2 = st.columns(2)
    driver_a = hc1.selectbox("Driver A", list(names), format_func=lambda i: names[i])
    driver_b = hc2.selectbox(
        "Driver B", list(names), format_func=lambda i: names[i],
        index=min(1, len(names) - 1),
    )
    if driver_a == driver_b:
        st.caption("Pick two different drivers.")
    else:
        h2h = pred_svc.head_to_head(race_id, driver_a, driver_b)
        if h2h["a_prob"] is None:
            st.caption("No model output for this race yet.")
        else:
            m1, m2 = st.columns(2)
            m1.metric(names[driver_a], format_percentage(h2h["a_prob"]))
            m2.metric(names[driver_b], format_percentage(h2h["b_prob"]))
