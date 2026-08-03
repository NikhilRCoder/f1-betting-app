"""Model Testing page — backtesting and comparison.

Thin view. Runs a leak-free season backtest via ``PredictionService`` and renders
accuracy metrics, a calibration plot and feature importances.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.prediction_service import PredictionService, build_default_models
from services.race_service import RaceService
from utilities.ui import bootstrap_page
from visualizations import charts, theme

bootstrap_page("Model Testing", icon="🧪")


@st.cache_resource
def _services() -> tuple[RaceService, PredictionService]:
    return RaceService(), PredictionService()


races_svc, pred_svc = _services()
seasons = races_svc.list_seasons()

if not seasons:
    st.info("No data yet. Import races/results on **Settings** to run backtests.")
    st.stop()

col1, col2 = st.columns(2)
season = col1.selectbox("Backtest season", options=seasons)
all_models = [m.name for m in build_default_models()]
chosen = col2.multiselect("Models", options=all_models, default=all_models)

bcol1, bcol2 = st.columns([1, 1])
if bcol1.button("Run backtest", type="primary"):
    with st.spinner("Retraining before each race and scoring…"):
        st.session_state["bt"] = pred_svc.backtest(season, model_names=chosen)

# Calibration: fit an isotonic map on out-of-sample ensemble predictions so the
# probabilities used by the recommendation engine match observed frequencies.
if bcol2.button("Calibrate ensemble on all data"):
    with st.spinner("Fitting probability calibration (walk-forward)…"):
        cal = pred_svc.build_calibrator()
    if cal.fitted:
        st.success(
            "Calibration fitted and saved. The Recommendations engine now uses "
            "calibrated probabilities."
        )
    else:
        st.warning(
            "Not enough historical data to calibrate yet — load more seasons and "
            "retry."
        )

bt = st.session_state.get("bt")
if not bt:
    st.caption(
        "Pick a season and models, then **Run backtest**. Each race is predicted "
        "using only data from earlier races (no look-ahead)."
    )
    st.stop()

if bt["n_races"] == 0:
    st.warning(
        "Not enough prior history in this season to backtest. Try a later season "
        "once more races are loaded."
    )
    st.stop()

st.caption(f"Backtested {bt['n_races']} races in {season}.")

# ── Metrics table ────────────────────────────────────────────────────
st.markdown("#### Accuracy metrics")
metrics_df = pd.DataFrame(bt["metrics"]).T.reset_index(names="model")
st.dataframe(metrics_df, use_container_width=True, hide_index=True)
st.caption("Lower log loss / Brier is better; higher accuracy is better.")

# ── Calibration plot ─────────────────────────────────────────────────
st.markdown("#### Calibration")
fig = go.Figure()
fig.add_scatter(
    x=[0, 1], y=[0, 1], mode="lines", name="Perfect",
    line=dict(dash="dash", color=theme.GRID),
)
for i, (model_name, points) in enumerate(bt["calibration"].items()):
    if not points:
        continue
    pts = pd.DataFrame(points)
    fig.add_scatter(
        x=pts["predicted"], y=pts["observed"], mode="lines+markers", name=model_name,
        line=dict(color=theme.CATEGORICAL[i % len(theme.CATEGORICAL)]),
    )
fig.update_layout(xaxis_title="Predicted probability", yaxis_title="Observed frequency")
st.plotly_chart(theme.apply_theme(fig), use_container_width=True)

# ── Feature importance ───────────────────────────────────────────────
st.markdown("#### Feature importance")
importances = {
    name: imp for name, imp in bt["feature_importance"].items() if imp
}
if importances:
    model_pick = st.selectbox("Model", options=list(importances))
    imp = importances[model_pick]
    imp_df = pd.DataFrame(
        sorted(imp.items(), key=lambda kv: kv[1], reverse=True),
        columns=["feature", "importance"],
    )
    st.plotly_chart(
        charts.bar_chart(
            imp_df["feature"].tolist(), imp_df["importance"].tolist(), y_title="Importance"
        ),
        use_container_width=True,
    )
