"""Settings page — configuration and database management.

Thin view. The database-stats section is live now; CSV import and model/
bankroll configuration arrive in later phases.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from database.connection import get_connection
from utilities.ui import bootstrap_page

bootstrap_page("Settings", icon="⚙️")

# ── Database stats (live) ────────────────────────────────────────────
st.subheader("Database")
st.caption(f"Location: `{settings.DATABASE_PATH}`")

_TABLES = (
    "drivers",
    "constructors",
    "circuits",
    "seasons",
    "races",
    "results",
    "qualifying",
    "pit_stops",
    "weather",
    "odds_history",
    "model_predictions",
    "recommendations",
    "manual_notes",
    "bet_tracker",
)


@st.cache_data(ttl=30)
def _table_counts() -> pd.DataFrame:
    """Return a table of row counts per schema table."""
    rows = []
    with get_connection() as conn:
        for table in _TABLES:
            count = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            rows.append({"table": table, "rows": count})
    return pd.DataFrame(rows)


counts = _table_counts()
st.dataframe(counts, use_container_width=True, hide_index=True)
if counts["rows"].sum() == 0:
    st.info(
        "The database is empty. CSV import (Phase 2) will populate it from "
        "Ergast dumps."
    )

# ── Placeholders for later phases ────────────────────────────────────
st.divider()
st.subheader("CSV Import")
st.caption("Phase 2 — upload a CSV, map it to a table, preview and import.")

st.divider()
st.subheader("Model & Bankroll Configuration")
st.caption(
    "Phase 4/5 — active models, ensemble weights, starting bankroll and "
    "default Kelly fraction."
)
