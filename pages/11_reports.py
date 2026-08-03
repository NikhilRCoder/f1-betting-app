"""Reports page — export generation.

Thin view. Generates CSV/Excel exports and a pre-race PDF via ``ReportService``
and offers each file for download.
"""
from __future__ import annotations

import streamlit as st

from services.race_service import RaceService
from services.report_service import ReportService
from utilities.ui import bootstrap_page

bootstrap_page("Reports", icon="📄")


@st.cache_resource
def _services() -> tuple[RaceService, ReportService]:
    return RaceService(), ReportService()


races_svc, report_svc = _services()
seasons = races_svc.list_seasons()

if not seasons:
    st.info("No races yet. Import data on the **Settings** page first.")
    st.stop()

col1, col2 = st.columns(2)
season = col1.selectbox("Season", options=seasons)
races = races_svc.races_for_season(season)
race_names = {r["id"]: f"R{r['round']} — {r['name']}" for r in races}
race_id = col2.selectbox("Race", options=list(race_names), format_func=lambda i: race_names[i])


def _offer(path, label: str, mime: str) -> None:
    """Read a generated file and render a download button."""
    with open(path, "rb") as fh:
        st.download_button(label, data=fh.read(), file_name=path.name, mime=mime)


st.markdown("#### CSV / Excel exports")
c1, c2, c3, c4 = st.columns(4)
if c1.button("Recommendations CSV"):
    _offer(report_svc.export_recommendations_csv(race_id), "Download CSV", "text/csv")
if c2.button("Odds CSV"):
    _offer(report_svc.export_odds_csv(race_id), "Download CSV", "text/csv")
if c3.button("Predictions CSV"):
    _offer(report_svc.export_predictions_csv(race_id), "Download CSV", "text/csv")
if c4.button("Recommendations Excel"):
    _offer(
        report_svc.export_recommendations_excel(race_id),
        "Download Excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.markdown("#### Pre-race PDF report")
st.caption("Race header plus the current recommendations table.")
if st.button("Generate pre-race PDF", type="primary"):
    try:
        path = report_svc.generate_prerace_pdf(race_id)
        st.success(f"Generated {path.name}")
        _offer(path, "Download PDF", "application/pdf")
    except Exception as exc:  # noqa: BLE001 - surface generation errors to the user
        st.error(f"PDF generation failed: {exc}")
