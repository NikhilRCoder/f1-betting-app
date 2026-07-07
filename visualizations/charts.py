"""Core Plotly chart builders.

Each function returns a themed :class:`plotly.graph_objects.Figure`. Builders are
presentation-only: callers pass plain sequences/DataFrames, keeping charts
decoupled from the data and service layers.
"""
from __future__ import annotations

from typing import Sequence

import plotly.graph_objects as go

from visualizations import theme


def line_chart(
    x: Sequence, y: Sequence, *, title: str = "", x_title: str = "", y_title: str = ""
) -> go.Figure:
    """Return a themed line chart (e.g. form or odds over time)."""
    fig = go.Figure(go.Scatter(x=list(x), y=list(y), mode="lines+markers"))
    fig.update_layout(title=title, xaxis_title=x_title, yaxis_title=y_title)
    return theme.apply_theme(fig)


def bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    color: str | None = None,
) -> go.Figure:
    """Return a themed bar chart (e.g. head-to-head, positions gained)."""
    fig = go.Figure(
        go.Bar(
            x=list(labels),
            y=list(values),
            marker_color=color or theme.ACCENT_BLUE,
        )
    )
    fig.update_layout(title=title, xaxis_title=x_title, yaxis_title=y_title)
    return theme.apply_theme(fig)


def histogram(
    values: Sequence[float], *, title: str = "", x_title: str = "", nbins: int = 30
) -> go.Figure:
    """Return a themed histogram (e.g. Monte Carlo outputs, deltas)."""
    fig = go.Figure(go.Histogram(x=list(values), nbinsx=nbins))
    fig.update_layout(title=title, xaxis_title=x_title, yaxis_title="Frequency")
    return theme.apply_theme(fig)


def scatter(
    x: Sequence[float],
    y: Sequence[float],
    *,
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    text: Sequence[str] | None = None,
) -> go.Figure:
    """Return a themed scatter plot (e.g. grid vs finish, prob vs odds)."""
    fig = go.Figure(
        go.Scatter(
            x=list(x),
            y=list(y),
            mode="markers",
            text=list(text) if text is not None else None,
            marker=dict(size=9, color=theme.ACCENT_YELLOW),
        )
    )
    fig.update_layout(title=title, xaxis_title=x_title, yaxis_title=y_title)
    return theme.apply_theme(fig)


def gauge(
    value: float, *, title: str = "", max_value: float = 100.0
) -> go.Figure:
    """Return a themed gauge chart (e.g. a confidence meter)."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title},
            gauge={
                "axis": {"range": [0, max_value]},
                "bar": {"color": theme.ACCENT_GREEN},
                "bordercolor": theme.GRID,
            },
        )
    )
    return theme.apply_theme(fig)


def probability_comparison(
    labels: Sequence[str],
    model_probs: Sequence[float],
    implied_probs: Sequence[float],
    *,
    title: str = "Model vs Bookmaker",
) -> go.Figure:
    """Return a grouped bar chart comparing model and implied probabilities."""
    fig = go.Figure()
    fig.add_bar(
        x=list(labels), y=list(model_probs), name="Model", marker_color=theme.ACCENT_GREEN
    )
    fig.add_bar(
        x=list(labels),
        y=list(implied_probs),
        name="Bookmaker",
        marker_color=theme.ACCENT_RED,
    )
    fig.update_layout(title=title, barmode="group", yaxis_title="Probability")
    return theme.apply_theme(fig)
