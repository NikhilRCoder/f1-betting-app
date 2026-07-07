"""Heatmap builders (performance grids, correlation matrices)."""
from __future__ import annotations

from typing import Sequence

import plotly.graph_objects as go

from visualizations import theme

# Dark-friendly diverging-ish colourscale using the PitWall accents.
_COLORSCALE = [
    [0.0, theme.ACCENT_GREEN],
    [0.5, theme.BG_PANEL],
    [1.0, theme.ACCENT_RED],
]


def heatmap(
    z: Sequence[Sequence[float]],
    x_labels: Sequence[str],
    y_labels: Sequence[str],
    *,
    title: str = "",
    reverse_scale: bool = False,
) -> go.Figure:
    """Return a themed heatmap.

    Args:
        z: 2-D matrix of values (rows correspond to ``y_labels``).
        x_labels: Column labels.
        y_labels: Row labels.
        title: Chart title.
        reverse_scale: Flip the colourscale (useful when lower is better, e.g.
            finishing position).

    Returns:
        A themed heatmap figure.
    """
    fig = go.Figure(
        go.Heatmap(
            z=[list(row) for row in z],
            x=list(x_labels),
            y=list(y_labels),
            colorscale=_COLORSCALE,
            reversescale=reverse_scale,
        )
    )
    fig.update_layout(title=title)
    return theme.apply_theme(fig)


def correlation_heatmap(
    matrix: Sequence[Sequence[float]], labels: Sequence[str], *, title: str = ""
) -> go.Figure:
    """Return a themed correlation heatmap over a square matrix in ``[-1, 1]``."""
    fig = go.Figure(
        go.Heatmap(
            z=[list(row) for row in matrix],
            x=list(labels),
            y=list(labels),
            colorscale=_COLORSCALE,
            zmid=0,
        )
    )
    fig.update_layout(title=title)
    return theme.apply_theme(fig)
