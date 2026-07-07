"""Dashboard page — home / overview.

Thin view. Surfaces the latest race result, season standings, data coverage and
full bet-tracking P&L (summary, timeline, by-market) via ``RaceService`` and
``BetService``. Bets can be logged and settled here.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from database.repositories.drivers import DriverRepository
from services.bet_service import BetService
from services.race_service import RaceService
from utilities.formatters import format_currency, format_percentage
from utilities.ui import bootstrap_page
from visualizations import charts

bootstrap_page("Dashboard", icon="📊")


@st.cache_resource
def _services() -> tuple[RaceService, BetService, DriverRepository]:
    return RaceService(), BetService(), DriverRepository()


race_svc, bet_svc, drivers_repo = _services()
seasons = race_svc.list_seasons()

if not seasons:
    st.info(
        "Welcome to **PitWall**. The database is empty — head to the "
        "**Settings** page to import Ergast CSV data, then return here."
    )
    st.stop()

# ── Latest race ──────────────────────────────────────────────────────
latest = race_svc.latest_race()
if latest:
    st.markdown(f"#### Latest race — {latest['name']} ({latest['season']})")
    st.caption(f"{latest['circuit_name']}, {latest['country']} · {latest['date']}")
    results = race_svc.race_results(latest["id"])
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

# ── P&L summary ──────────────────────────────────────────────────────
st.divider()
st.markdown("#### Profit & Loss")
pnl = bet_svc.pnl_summary()
if pnl["total_bets"] == 0:
    st.caption("No settled bets yet. Log and settle bets below to track P&L.")
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bets", pnl["total_bets"])
    c2.metric("Win rate", format_percentage(pnl["win_rate"]))
    c3.metric("Staked", format_currency(pnl["total_staked"]))
    c4.metric("P&L", format_currency(pnl["total_profit_loss"]))
    c5.metric("ROI", f"{pnl['roi_pct']:.1f}%")

    timeline = bet_svc.pnl_timeline()
    if timeline:
        tdf = pd.DataFrame(timeline)
        st.plotly_chart(
            charts.line_chart(
                list(range(1, len(tdf) + 1)),
                tdf["cumulative_pl"].tolist(),
                title="Cumulative P&L",
                x_title="Settled bet #",
                y_title="Cumulative P&L",
            ),
            use_container_width=True,
        )

    by_market = bet_svc.performance_by("market")
    if by_market:
        st.markdown("##### By market")
        st.dataframe(pd.DataFrame(by_market), use_container_width=True, hide_index=True)

# ── Bet management ───────────────────────────────────────────────────
with st.expander("Log / settle bets"):
    driver_names = {
        d["id"]: f"{d['full_name']} ({d['code']})"
        for d in drivers_repo.get_all(order_by="last_name")
    }
    races = race_svc.races_for_season(seasons[0])
    race_names = {r["id"]: f"R{r['round']} — {r['name']}" for r in races}

    st.markdown("**Place a bet**")
    with st.form("place_bet"):
        cc = st.columns(4)
        b_race = cc[0].selectbox("Race", list(race_names), format_func=lambda i: race_names[i])
        b_driver = cc[1].selectbox(
            "Driver", list(driver_names), format_func=lambda i: driver_names[i]
        )
        b_odds = cc[2].number_input("Odds taken", min_value=1.01, value=3.0, step=0.05)
        b_stake = cc[3].number_input("Stake", min_value=0.01, value=10.0, step=1.0)
        if st.form_submit_button("Log bet"):
            try:
                bet_svc.place_bet(b_race, b_driver, "race_winner", b_odds, b_stake)
                st.success("Bet logged.")
            except ValueError as exc:
                st.error(str(exc))

    bets = bet_svc.list_bets()
    if bets:
        st.markdown("**Open & settled bets**")
        st.dataframe(
            pd.DataFrame(bets)[
                ["id", "race_name", "code", "odds_taken", "stake", "result", "profit_loss"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        pending = [b for b in bets if b["result"] == "pending"]
        if pending:
            sc = st.columns(3)
            settle_id = sc[0].selectbox("Settle bet id", [b["id"] for b in pending])
            outcome = sc[1].selectbox("Result", ["win", "loss", "void"])
            if sc[2].button("Settle"):
                bet_svc.settle_bet(settle_id, outcome)
                st.success(f"Bet {settle_id} settled as {outcome}.")
                st.rerun()

# ── Coverage ─────────────────────────────────────────────────────────
st.divider()
st.markdown("#### Data coverage")
c1, c2 = st.columns(2)
c1.metric("Seasons", len(seasons))
c2.metric("Range", f"{min(seasons)}–{max(seasons)}")
