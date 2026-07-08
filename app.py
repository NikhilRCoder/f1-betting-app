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
from utilities.ui import inject_theme
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
    inject_theme()

    st.markdown(
        f"""
        <div class="pw-header">
            <p class="pw-title">{settings.APP_ICON}&nbsp;{settings.APP_NAME}</p>
            <p class="pw-sub">{settings.APP_TAGLINE} · v{settings.APP_VERSION}</p>
        </div>
        <hr class="pw-rule"/>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "**PitWall** is a quantitative research platform for Formula One betting "
        "markets — it models race outcomes, compares model probabilities against "
        "bookmaker odds, detects value, and tracks profit & loss."
    )

    st.markdown(
        """
        <div class="pw-cards">
            <div class="pw-card">
                <div class="pw-ico">📊</div><h4>Analyse</h4>
                <p>Drivers, constructors and circuits, backed by historical data.</p>
            </div>
            <div class="pw-card">
                <div class="pw-ico">🎯</div><h4>Predict</h4>
                <p>An ensemble of models produces calibrated outcome probabilities.</p>
            </div>
            <div class="pw-card">
                <div class="pw-ico">💰</div><h4>Profit</h4>
                <p>Value detection, Kelly staking and bankroll-aware recommendations.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Get started in the sidebar — open **Settings** to import data (try "
        "**Fetch online**), then explore **Recommendations** and the analysis "
        "pages."
    )


if __name__ == "__main__":
    main()
