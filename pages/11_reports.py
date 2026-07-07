"""Reports page — export generation.

Thin view. Will generate pre/post-race PDF reports and CSV/Excel exports via
``report_service``.
"""
from __future__ import annotations

from utilities.ui import bootstrap_page, coming_soon

bootstrap_page("Reports", icon="📄")
coming_soon(
    phase="Phase 5",
    description=(
        "Pre-race and post-race PDF reports, plus CSV/Excel exports of "
        "recommendations, odds history and prediction history."
    ),
)
