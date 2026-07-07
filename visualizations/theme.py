"""Plotly theme — dark, Bloomberg-Terminal aesthetic.

Defines the shared colour palette and a reusable Plotly layout template so every
chart in PitWall renders with a consistent look. UI-framework agnostic: this
module only depends on Plotly.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# ═══════════════════════════════════════════════════════════════════
# Palette
# ═══════════════════════════════════════════════════════════════════
BG_DARK: str = "#0a0a0f"
BG_PANEL: str = "#111118"
GRID: str = "#1a1a2e"
TEXT: str = "#c8c8d4"

ACCENT_RED: str = "#e63946"
ACCENT_GREEN: str = "#06d6a0"
ACCENT_BLUE: str = "#118ab2"
ACCENT_YELLOW: str = "#ffd166"

# Ordered categorical sequence for multi-series charts.
CATEGORICAL: tuple[str, ...] = (
    ACCENT_BLUE,
    ACCENT_RED,
    ACCENT_GREEN,
    ACCENT_YELLOW,
    "#8338ec",
    "#fb8500",
    "#4cc9f0",
    "#ef476f",
)

FONT_DATA: str = "monospace"
FONT_LABEL: str = "sans-serif"

# Semantic colours for betting verdicts (reused by cards and tables).
VERDICT_COLORS: dict[str, str] = {
    "STRONG_BET": ACCENT_GREEN,
    "SMALL_EDGE": ACCENT_BLUE,
    "NO_BET": TEXT,
    "AVOID": ACCENT_RED,
}

_TEMPLATE_NAME: str = "pitwall"


def _build_template() -> go.layout.Template:
    """Construct the PitWall Plotly template."""
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor=BG_DARK,
        plot_bgcolor=BG_PANEL,
        font=dict(color=TEXT, family=FONT_LABEL, size=13),
        title=dict(font=dict(color=TEXT, family=FONT_LABEL, size=18)),
        xaxis=dict(
            gridcolor=GRID,
            zerolinecolor=GRID,
            linecolor=GRID,
            tickfont=dict(family=FONT_DATA),
        ),
        yaxis=dict(
            gridcolor=GRID,
            zerolinecolor=GRID,
            linecolor=GRID,
            tickfont=dict(family=FONT_DATA),
        ),
        colorway=list(CATEGORICAL),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
        margin=dict(l=60, r=30, t=50, b=50),
    )
    return template


def register_theme() -> str:
    """Register the PitWall template with Plotly and make it the default.

    Idempotent — safe to call on every Streamlit rerun.

    Returns:
        The registered template name.
    """
    pio.templates[_TEMPLATE_NAME] = _build_template()
    pio.templates.default = _TEMPLATE_NAME
    return _TEMPLATE_NAME


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply the PitWall template to an existing figure and return it."""
    fig.update_layout(template=_TEMPLATE_NAME)
    return fig
