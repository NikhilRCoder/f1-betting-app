"""Settings page — configuration and database management.

Thin view. Live database stats and CSV import (Ergast bundle + single table);
model/bankroll configuration arrives in later polish.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from config import settings
from database.connection import get_connection
from database.seed import import_dataframe, seed_database, seed_from_uploaded
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
        "The database is empty. Use the **Import data** section below to load "
        "Ergast CSV files, then the analysis, model and recommendation pages "
        "come to life."
    )

# ── Import data (live) ───────────────────────────────────────────────
st.divider()
st.subheader("Import data")

_ERGAST_FILES = (
    "drivers.csv", "constructors.csv", "circuits.csv", "races.csv",
    "results.csv", "qualifying.csv", "pit_stops.csv", "status.csv",
)

bundle_tab, single_tab = st.tabs(["Ergast CSV bundle", "Single table CSV"])

# --- Ergast bundle: the reliable way to load real F1 data ---
with bundle_tab:
    st.caption(
        "Upload the standard Ergast CSV files (or point at a folder that "
        "contains them). Column mapping, driver codes, lap-time parsing and "
        "foreign keys are handled automatically. Re-importing is safe."
    )
    st.caption("Expected files: " + ", ".join(f"`{f}`" for f in _ERGAST_FILES))

    uploads = st.file_uploader(
        "Upload Ergast CSV files",
        type="csv",
        accept_multiple_files=True,
        key="ergast_uploads",
    )
    folder = st.text_input(
        "…or a folder path on this machine containing the CSVs",
        placeholder=str(settings.CSV_DIR),
    )

    if st.button("Import Ergast data", type="primary"):
        try:
            if uploads:
                result = seed_from_uploaded(uploads)
            elif folder.strip():
                result = seed_database(Path(folder.strip()))
            else:
                result = None
                st.warning("Upload files or enter a folder path first.")
            if result:
                total = sum(result.values())
                st.success(f"Imported {total:,} rows across {len(result)} tables.")
                st.dataframe(
                    pd.DataFrame(
                        sorted(result.items()), columns=["table", "rows imported"]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                _table_counts.clear()
        except Exception as exc:  # noqa: BLE001 - surface import errors to the user
            st.error(f"Import failed: {exc}")

# --- Single table: generic, for CSVs whose columns match a table ---
with single_tab:
    st.caption(
        "Upload one CSV whose column names already match a PitWall table. "
        "Unmatched columns are ignored; rows upsert by primary key."
    )
    target_table = st.selectbox("Target table", _TABLES)
    single = st.file_uploader("Upload CSV", type="csv", key="single_upload")
    if single is not None:
        preview = pd.read_csv(single)
        st.caption(f"Preview — {len(preview):,} rows, {len(preview.columns)} columns")
        st.dataframe(preview.head(10), use_container_width=True, hide_index=True)
        if st.button(f"Import into {target_table}"):
            try:
                n = import_dataframe(target_table, preview)
                st.success(f"Imported {n:,} rows into {target_table}.")
                _table_counts.clear()
            except Exception as exc:  # noqa: BLE001 - surface import errors
                st.error(f"Import failed: {exc}")

# ── Placeholder for later polish ─────────────────────────────────────
st.divider()
st.subheader("Model & Bankroll Configuration")
st.caption(
    "Later polish — active models, ensemble weights, starting bankroll and "
    "default Kelly fraction. For now these use the defaults in config/settings.py."
)
