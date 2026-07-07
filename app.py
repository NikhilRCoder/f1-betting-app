"""PitWall — F1 Betting Analytics Platform.

Streamlit entry point. Responsibilities:

* Configure logging and ensure runtime directories exist.
* Initialise the SQLite database (idempotent).
* Register the Plotly theme.
* Render the landing/overview shell.

Streamlit automatically discovers the numbered files in ``pages/`` and lists
them in the sidebar navigation. This module contains no business logic; it is a
thin bootstrap + landing view.
"""
from __future__ import annotations

import streamlit as st

from config import settings
from config.logging_config import get_logger
from database.connection import database_exists, initialize_database
from visualizations.theme import register_theme

logger = get_logger(__name__)


@st.cache_resource
def bootstrap() -> bool:
    """Run one-time application setup, cached for the server's lifetime.

    Returns:
        ``True`` once setup has completed successfully.
    """
    settings.ensure_directories()
    if not database_exists():
        logger.info("Database not found — initialising fresh schema.")
    initialize_database()
    register_theme()
    logger.info("%s v%s bootstrapped.", settings.APP_NAME, settings.APP_VERSION)
    return True


def main() -> None:
    """Render the landing page."""
    st.set_page_config(
        page_title=f"{settings.APP_NAME} · {settings.APP_TAGLINE}",
        page_icon=settings.APP_ICON,
        layout="wide",
    )
    bootstrap()

    st.title(f"{settings.APP_ICON}  {settings.APP_NAME}")
    st.subheader(settings.APP_TAGLINE)
    st.caption(f"v{settings.APP_VERSION}")

    st.markdown(
        """
        **PitWall** is a quantitative research platform for Formula One betting
        markets. It models race outcomes, compares model probabilities against
        bookmaker odds, detects value, and tracks profit & loss.

        Use the sidebar to navigate. Pages are delivered across five build
        phases — some are still placeholders while the data and model layers are
        wired up.
        """
    )

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📊 Analyse")
        st.caption("Drivers, constructors and circuits, backed by historical data.")
    with col2:
        st.markdown("### 🎯 Predict")
        st.caption("Ensemble models produce calibrated outcome probabilities.")
    with col3:
        st.markdown("### 💰 Profit")
        st.caption("Value detection, staking, and bankroll-aware recommendations.")

    st.divider()
    st.caption(
        "Select a page from the sidebar to begin. "
        "Start with **Settings** to import data, then **Odds** and "
        "**Recommendations**."
    )


if __name__ == "__main__":
    main()
