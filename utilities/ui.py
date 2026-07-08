"""Streamlit UI helpers and shared visual theme.

Thin, presentation-only chrome shared across pages so each page stays short and
consistent. This is the *only* utilities module that imports Streamlit; the pure
helpers live in :mod:`utilities.helpers`.

The look-and-feel is centralised here: :func:`bootstrap_page` injects one CSS
theme and a branded sidebar on every page, so the whole app stays cohesive.
Contains no business logic — pages still call services for data.
"""
from __future__ import annotations

import streamlit as st

from config import settings
from visualizations import theme

# ── Design tokens (derived from the Plotly theme so charts + chrome match) ──
_MUTED = "#8a8a9a"
_CARD_BG = "#14141c"
_FONT_UI = (
    "'Inter','Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"
)
_FONT_MONO = "'JetBrains Mono','SF Mono','Cascadia Mono',Consolas,monospace"

_THEME_CSS = f"""
<style>
/* ---- Base typography & layout ---- */
html, body, [class*="css"], .stMarkdown, button, input, textarea, select {{
    font-family: {_FONT_UI};
}}
.block-container {{
    padding-top: 2.2rem;
    padding-bottom: 3.5rem;
    max-width: 1360px;
}}
h1, h2, h3 {{ letter-spacing: -0.015em; }}
h1 {{ font-weight: 750; }}
h2 {{ font-weight: 680; margin-top: 0.4rem; }}
h3 {{ font-weight: 620; color: {theme.TEXT}; }}
a {{ color: {theme.ACCENT_BLUE}; }}

/* ---- Page header ---- */
.pw-header {{ margin-bottom: .2rem; }}
.pw-title {{
    font-size: 1.95rem; font-weight: 780; letter-spacing: -0.025em; margin: 0;
    display: flex; align-items: center; gap: .55rem;
}}
.pw-sub {{ color: {_MUTED}; font-size: .95rem; margin: .2rem 0 0; }}
.pw-rule {{
    height: 3px; border: 0; border-radius: 3px; margin: .55rem 0 1.4rem;
    background: linear-gradient(90deg, {theme.ACCENT_RED} 0%,
        {theme.ACCENT_BLUE} 38%, rgba(26,26,46,0) 80%);
}}

/* ---- Metric cards ---- */
[data-testid="stMetric"] {{
    background: {_CARD_BG};
    border: 1px solid {theme.GRID};
    border-radius: 12px;
    padding: 14px 16px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,.45);
    transition: border-color .15s ease, transform .15s ease;
}}
[data-testid="stMetric"]:hover {{
    border-color: {theme.ACCENT_BLUE}; transform: translateY(-1px);
}}
[data-testid="stMetricLabel"] p {{
    text-transform: uppercase; letter-spacing: .09em;
    font-size: .72rem; color: {_MUTED};
}}
[data-testid="stMetricValue"] {{
    font-family: {_FONT_MONO}; font-weight: 600; letter-spacing: -0.01em;
}}

/* ---- Buttons ---- */
.stButton > button, .stDownloadButton > button {{
    border-radius: 10px; font-weight: 600; border: 1px solid {theme.GRID};
    transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.4);
    border-color: {theme.ACCENT_BLUE};
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {theme.ACCENT_RED}, #b52a37);
    border: 0; color: #fff;
}}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {{
    background: #0c0c12; border-right: 1px solid {theme.GRID};
}}
.pw-brand {{ padding: 4px 2px 14px; margin-bottom: 8px;
    border-bottom: 1px solid {theme.GRID}; }}
.pw-brand-name {{ font-size: 1.3rem; font-weight: 800; letter-spacing: -.02em; }}
.pw-brand-tag {{ font-size: .68rem; text-transform: uppercase;
    letter-spacing: .16em; color: {_MUTED}; margin-top: 1px; }}
[data-testid="stSidebarNav"] ul {{ gap: 1px; }}
[data-testid="stSidebarNav"] a {{ border-radius: 8px; }}
[data-testid="stSidebarNav"] a:hover {{ background: {theme.GRID}; }}

/* ---- Tabs ---- */
[data-baseweb="tab-list"] {{ gap: 3px; border-bottom: 1px solid {theme.GRID}; }}
[data-baseweb="tab"] {{ border-radius: 8px 8px 0 0; padding: 6px 14px; }}
button[aria-selected="true"][data-baseweb="tab"] {{ color: {theme.ACCENT_YELLOW}; }}

/* ---- Containers ---- */
[data-testid="stDataFrame"], [data-testid="stExpander"] {{
    border: 1px solid {theme.GRID}; border-radius: 10px;
}}
[data-testid="stAlert"] {{ border-radius: 10px; }}
hr {{ border-color: {theme.GRID}; }}
[data-testid="stMetricValue"] div {{ color: {theme.TEXT}; }}

/* ---- Landing cards ---- */
.pw-cards {{ display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 16px; margin: .4rem 0 1rem; }}
.pw-card {{ background: {_CARD_BG}; border: 1px solid {theme.GRID};
    border-radius: 14px; padding: 18px 18px 16px; }}
.pw-card .pw-ico {{ font-size: 1.5rem; }}
.pw-card h4 {{ margin: .5rem 0 .3rem; font-size: 1.05rem; font-weight: 680; }}
.pw-card p {{ color: {_MUTED}; font-size: .88rem; margin: 0; line-height: 1.5; }}
@media (max-width: 900px) {{ .pw-cards {{ grid-template-columns: 1fr; }} }}
</style>
"""


def inject_theme() -> None:
    """Inject the shared CSS theme and the branded sidebar header.

    Safe to call on every rerun and every page — Streamlit de-duplicates the
    resulting DOM.
    """
    st.markdown(_THEME_CSS, unsafe_allow_html=True)
    st.sidebar.markdown(
        f"""
        <div class="pw-brand">
            <div class="pw-brand-name">{settings.APP_ICON} {settings.APP_NAME}</div>
            <div class="pw-brand-tag">{settings.APP_TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bootstrap_page(
    title: str, icon: str = settings.APP_ICON, subtitle: str | None = None
) -> None:
    """Apply shared page config, inject the theme, and render the page header.

    Args:
        title: The page title (browser tab + on-page heading).
        icon: Emoji/icon for the tab and heading.
        subtitle: Optional one-line description shown under the title.
    """
    st.set_page_config(
        page_title=f"{settings.APP_NAME} · {title}",
        page_icon=icon,
        layout="wide",
    )
    inject_theme()
    sub_html = f'<p class="pw-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="pw-header">
            <p class="pw-title">{icon}&nbsp;{title}</p>
            {sub_html}
        </div>
        <hr class="pw-rule"/>
        """,
        unsafe_allow_html=True,
    )


def coming_soon(phase: str, description: str) -> None:
    """Render a standard placeholder for pages not yet implemented."""
    st.info(f"**Coming soon** — planned for **{phase}**.")
    st.caption(description)
