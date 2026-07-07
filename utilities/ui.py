"""Streamlit UI helpers.

Thin, presentation-only widgets shared across pages so that each page file stays
short and free of duplicated chrome. This is the *only* utilities module that
imports Streamlit; the pure helpers live in :mod:`utilities.helpers`.

Contains no business logic — pages still call services for data.
"""
from __future__ import annotations

import streamlit as st

from config import settings


def bootstrap_page(title: str, icon: str = settings.APP_ICON) -> None:
    """Apply shared page config and render a consistent page header.

    Args:
        title: The page title shown in the browser tab and as an ``H1``.
        icon: Emoji/icon for the browser tab.
    """
    st.set_page_config(
        page_title=f"{settings.APP_NAME} · {title}",
        page_icon=icon,
        layout="wide",
    )
    st.title(f"{icon}  {title}")


def coming_soon(phase: str, description: str) -> None:
    """Render a standard placeholder for pages not yet implemented.

    Args:
        phase: The build phase in which this page is delivered.
        description: One-line summary of what the page will contain.
    """
    st.info(f"**Page coming soon** — planned for **{phase}**.")
    st.caption(description)
