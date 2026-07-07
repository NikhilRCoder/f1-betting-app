"""Playground page — interactive calculators.

Thin view. Wires the pure ``calculators`` package directly to interactive
widgets. Model-driven tools (Monte Carlo, what-if) arrive in Phase 4; the
odds/staking calculators below are live now.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from calculators import (
    arbitrage,
    bankroll,
    dutch,
    expected_value,
    kelly,
    overround,
    probability,
)
from config import settings
from utilities.formatters import (
    format_currency,
    format_percentage,
    format_signed_percentage,
)
from utilities.ui import bootstrap_page

bootstrap_page("Playground", icon="🧮")
st.caption("Interactive betting calculators, powered by the pure calculators package.")

tabs = st.tabs(
    [
        "Converter",
        "Expected Value",
        "Kelly",
        "Arbitrage",
        "Dutching",
        "Overround",
        "Bankroll",
        "Risk of Ruin",
    ]
)

# ── Odds converter ───────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Odds Converter")
    dec = st.number_input(
        "Decimal odds", min_value=1.01, value=2.50, step=0.01, key="conv_dec"
    )
    result = probability.convert_all(dec, "decimal")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Decimal", f"{result['decimal']:.2f}")
    c2.metric("Fractional", result["fractional"])
    c3.metric("American", result["american"])
    c4.metric("Implied Prob", format_percentage(result["implied_probability"]))

# ── Expected value ───────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Expected Value")
    prob = st.slider("Model probability", 0.0, 1.0, 0.45, 0.01, key="ev_prob")
    ev_odds = st.number_input(
        "Decimal odds", min_value=1.01, value=2.50, step=0.01, key="ev_odds"
    )
    ev_pct = expected_value.calculate_ev_percentage(prob, ev_odds)
    st.metric("Expected Value", f"{ev_pct:+.2f}%")
    st.caption(
        "Positive EV means the model rates the outcome more likely than the "
        "price implies."
    )

# ── Kelly ────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Kelly Stake")
    k_prob = st.slider("Win probability", 0.0, 1.0, 0.45, 0.01, key="k_prob")
    k_odds = st.number_input(
        "Decimal odds", min_value=1.01, value=2.50, step=0.01, key="k_odds"
    )
    k_bankroll = st.number_input(
        "Bankroll", min_value=0.0, value=settings.DEFAULT_BANKROLL, step=50.0
    )
    k_fraction = st.slider(
        "Kelly fraction", 0.0, 1.0, settings.DEFAULT_KELLY_FRACTION, 0.05
    )
    full = kelly.full_kelly(k_prob, k_odds)
    frac = kelly.fractional_kelly(k_prob, k_odds, k_fraction)
    stake = kelly.kelly_stake(k_bankroll, k_prob, k_odds, k_fraction)
    c1, c2, c3 = st.columns(3)
    c1.metric("Full Kelly", format_percentage(full))
    c2.metric(f"{k_fraction:.0%} Kelly", format_percentage(frac))
    c3.metric("Stake", format_currency(stake))

# ── Arbitrage ────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Arbitrage Checker")
    raw = st.text_input(
        "Decimal odds (comma-separated)", value="2.10, 2.05", key="arb_odds"
    )
    total = st.number_input("Total stake", min_value=1.0, value=100.0, step=10.0)
    try:
        odds_list = [float(x) for x in raw.split(",") if x.strip()]
        is_arb, margin = arbitrage.detect_arb(odds_list)
        if is_arb:
            st.success(f"Arbitrage found — guaranteed margin {margin:.2%}")
            stakes = arbitrage.arb_stakes(odds_list, total)
            for i, (o, s) in enumerate(zip(odds_list, stakes), start=1):
                st.write(f"Outcome {i} @ {o:.2f} → stake {format_currency(s)}")
        else:
            st.warning(f"No arbitrage — book margin {(-margin):.2%}")
    except ValueError as exc:
        st.error(str(exc))

# ── Dutching ─────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("Dutch Calculator")
    raw = st.text_input(
        "Decimal odds (comma-separated)", value="3.0, 4.0, 5.0", key="dutch_odds"
    )
    total = st.number_input(
        "Total stake", min_value=1.0, value=100.0, step=10.0, key="dutch_total"
    )
    try:
        odds_list = [float(x) for x in raw.split(",") if x.strip()]
        stakes = dutch.dutch_stakes(odds_list, total)
        profit = dutch.dutch_profit(odds_list, total)
        for i, (o, s) in enumerate(zip(odds_list, stakes), start=1):
            st.write(f"Selection {i} @ {o:.2f} → stake {format_currency(s)}")
        st.metric("Guaranteed profit", format_currency(profit))
    except ValueError as exc:
        st.error(str(exc))

# ── Overround ────────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("Overround / True Probabilities")
    raw = st.text_input(
        "Decimal odds (comma-separated)", value="1.90, 1.90", key="or_odds"
    )
    try:
        odds_list = [float(x) for x in raw.split(",") if x.strip()]
        over = overround.calculate_overround(odds_list)
        trues = overround.true_probabilities(odds_list)
        st.metric("Overround", format_signed_percentage(over))
        for i, (o, p) in enumerate(zip(odds_list, trues), start=1):
            st.write(f"Outcome {i} @ {o:.2f} → true prob {format_percentage(p)}")
    except ValueError as exc:
        st.error(str(exc))

# ── Bankroll growth ──────────────────────────────────────────────────
with tabs[6]:
    st.subheader("Bankroll Growth Simulator")
    start = st.number_input(
        "Starting bankroll", min_value=0.0, value=settings.DEFAULT_BANKROLL, step=50.0
    )
    avg_ev = st.slider("Average EV per bet", 0.0, 0.20, 0.05, 0.01)
    bets = st.slider("Bets per race", 0, 10, 3)
    races = st.slider("Races", 1, 24, 22)
    trajectory = bankroll.growth_projection(start, avg_ev, bets, races)
    fig = go.Figure(go.Scatter(y=trajectory, mode="lines", line=dict(width=3)))
    fig.update_layout(
        title="Projected bankroll", xaxis_title="Race", yaxis_title="Bankroll"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Projected final bankroll", format_currency(trajectory[-1]))

# ── Risk of ruin ─────────────────────────────────────────────────────
with tabs[7]:
    st.subheader("Risk of Ruin")
    r_bankroll = st.number_input(
        "Bankroll", min_value=1.0, value=settings.DEFAULT_BANKROLL, step=50.0,
        key="ror_bank",
    )
    r_stake = st.number_input("Average stake", min_value=1.0, value=20.0, step=5.0)
    r_win = st.slider("Win rate", 0.0, 1.0, 0.40, 0.01)
    r_odds = st.number_input(
        "Average decimal odds", min_value=1.01, value=3.0, step=0.1, key="ror_odds"
    )
    ror = bankroll.risk_of_ruin(r_bankroll, r_stake, r_win, r_odds)
    st.metric("Estimated risk of ruin", format_percentage(ror, decimals=2))
    if ror >= 0.99:
        st.error("Negative edge — ruin is effectively certain over time.")
