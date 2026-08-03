"""Odds page — scraping and management.

Thin view. Scrape odds from a URL, add manual entries, and view the current
market with implied probabilities and overround via ``OddsService``.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from database.repositories.drivers import DriverRepository
from services.odds_service import OddsService
from services.race_service import RaceService
from utilities.formatters import format_percentage, format_signed_percentage
from utilities.ui import bootstrap_page

bootstrap_page("Odds", icon="💱")


@st.cache_resource
def _deps() -> tuple[OddsService, RaceService, DriverRepository]:
    return OddsService(), RaceService(), DriverRepository()


odds_svc, races_svc, drivers_repo = _deps()
seasons = races_svc.list_seasons()

if not seasons:
    st.info("No races yet. Import data on the **Settings** page first.")
    st.stop()

col1, col2, col3 = st.columns(3)
season = col1.selectbox("Season", options=seasons)
races = races_svc.races_for_season(season)
race_names = {r["id"]: f"R{r['round']} — {r['name']}" for r in races}
race_id = col2.selectbox("Race", options=list(race_names), format_func=lambda i: race_names[i])
market = col3.selectbox("Market", options=list(settings.MARKETS))

# ── Scrape from URL ──────────────────────────────────────────────────
st.markdown("#### Scrape from URL")
url = st.text_input("Odds page URL", placeholder="https://…")
bookmaker = st.text_input("Bookmaker label", value="scraped")
if st.button("Scrape & store", type="primary"):
    if not url.strip():
        st.warning("Enter a URL to scrape.")
    else:
        try:
            summary = odds_svc.scrape_and_store(url, race_id, market, bookmaker)
            st.success(
                f"Stored {summary['stored']} of {summary['total']} rows."
            )
            if summary["unmatched"]:
                st.caption("Unmatched drivers: " + ", ".join(summary["unmatched"][:20]))
        except Exception as exc:  # noqa: BLE001 - surface any scrape/network error
            st.error(f"Scrape failed: {exc}")

# ── Manual entry ─────────────────────────────────────────────────────
st.markdown("#### Manual entry")
drivers = drivers_repo.get_all(order_by="last_name")
driver_names = {d["id"]: f"{d['full_name']} ({d['code']})" for d in drivers}
with st.form("manual_odds"):
    c1, c2, c3 = st.columns(3)
    m_driver = c1.selectbox(
        "Driver", options=list(driver_names), format_func=lambda i: driver_names[i]
    )
    m_book = c2.text_input("Bookmaker", value="manual")
    m_odds = c3.number_input("Decimal odds", min_value=1.01, value=3.0, step=0.05)
    submitted = st.form_submit_button("Add odds")
    if submitted:
        try:
            odds_svc.add_manual_odds(race_id, m_driver, market, m_book, m_odds)
            st.success(f"Added {driver_names[m_driver]} @ {m_odds:.2f}")
        except ValueError as exc:
            st.error(str(exc))

# ── Current market ───────────────────────────────────────────────────
st.markdown("#### Current odds")
rows = odds_svc.get_market_table(race_id, market)
if rows:
    df = pd.DataFrame(rows)[
        ["driver", "code", "bookmaker", "odds_decimal", "implied_probability"]
    ]
    df["implied_probability"] = df["implied_probability"].map(
        lambda p: format_percentage(p) if p is not None else "—"
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    overround = odds_svc.market_overround(race_id, market)
    if overround is not None:
        st.metric("Market overround", format_signed_percentage(overround))
else:
    st.caption("No odds recorded for this race/market yet.")
