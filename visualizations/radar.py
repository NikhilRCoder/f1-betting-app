"""Radar (spider) chart builders for driver/constructor skill profiles."""
from __future__ import annotations

from typing import Mapping, Sequence

import plotly.graph_objects as go

from visualizations import theme


def radar_chart(
    metrics: Mapping[str, float], *, title: str = "", max_value: float = 100.0
) -> go.Figure:
    """Return a themed radar chart from an axis→value mapping.

    Args:
        metrics: Mapping of axis label to value (e.g. qualifying, race pace,
            consistency, wet, tyre management, overtaking), each in
            ``[0, max_value]``.
        title: Chart title.
        max_value: Upper bound of the radial axis.

    Returns:
        A themed radar figure.
    """
    axes = list(metrics.keys())
    values = list(metrics.values())
    # Close the polygon by repeating the first point.
    axes_closed = axes + axes[:1]
    values_closed = values + values[:1]

    fig = go.Figure(
        go.Scatterpolar(
            r=values_closed,
            theta=axes_closed,
            fill="toself",
            line=dict(color=theme.ACCENT_BLUE),
            fillcolor="rgba(17, 138, 178, 0.35)",
        )
    )
    fig.update_layout(
        title=title,
        polar=dict(
            bgcolor=theme.BG_PANEL,
            radialaxis=dict(visible=True, range=[0, max_value], gridcolor=theme.GRID),
            angularaxis=dict(gridcolor=theme.GRID),
        ),
        showlegend=False,
    )
    return theme.apply_theme(fig)


def compare_radar(
    axes: Sequence[str],
    series: Mapping[str, Sequence[float]],
    *,
    title: str = "",
    max_value: float = 100.0,
) -> go.Figure:
    """Return a radar chart overlaying multiple named series (e.g. two drivers)."""
    fig = go.Figure()
    axes_closed = list(axes) + list(axes[:1])
    for i, (name, values) in enumerate(series.items()):
        vals = list(values) + list(values[:1])
        color = theme.CATEGORICAL[i % len(theme.CATEGORICAL)]
        fig.add_trace(
            go.Scatterpolar(
                r=vals, theta=axes_closed, name=name, line=dict(color=color)
            )
        )
    fig.update_layout(
        title=title,
        polar=dict(
            bgcolor=theme.BG_PANEL,
            radialaxis=dict(visible=True, range=[0, max_value], gridcolor=theme.GRID),
            angularaxis=dict(gridcolor=theme.GRID),
        ),
    )
    return theme.apply_theme(fig)
