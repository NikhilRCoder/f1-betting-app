"""Circuit Analysis page.

Thin view. Renders physical stats, race characteristics, grid importance and the
most successful drivers/constructors via ``CircuitService``.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.circuit_service import CircuitService
from utilities.formatters import format_percentage
from utilities.ui import bootstrap_page

bootstrap_page("Circuit Analysis", icon="🛣️")


@st.cache_resource
def _service() -> CircuitService:
    return CircuitService()


service = _service()
circuits = service.list_circuits()

if not circuits:
    st.info(
        "No circuits in the database yet. Import data on the **Settings** page "
        "to populate circuit analysis."
    )
    st.stop()

names = {c["id"]: f"{c['name']} ({c['country']})" for c in circuits}
circuit_id = st.selectbox("Circuit", options=list(names), format_func=lambda i: names[i])

profile = service.get_profile(circuit_id)
circuit = profile["circuit"]
chars = profile["characteristics"]

st.subheader(circuit["name"])

# ── Physical stats ───────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Length (km)", circuit.get("length_km") or "—")
c2.metric("Corners", circuit.get("corners") or "—")
c3.metric("DRS zones", circuit.get("drs_zones") or "—")
c4.metric("Type", circuit.get("circuit_type") or "—")

# ── Race characteristics ─────────────────────────────────────────────
st.markdown("#### Race history")
if chars.get("races"):
    a, b, c, d = st.columns(4)
    a.metric("Races", chars["races"])
    a2 = chars.get("avg_safety_cars")
    b.metric("Avg safety cars", a2 if a2 is not None else "—")
    c.metric("Total DNFs", chars.get("total_dnfs", 0))
    gi = profile["grid_importance"]
    d.metric("Grid→finish corr", gi if gi is not None else "—")
    pc = profile["pole_conversion"]
    st.caption(
        f"Pole-to-win conversion: {format_percentage(pc) if pc is not None else '—'}"
    )
else:
    st.caption("No races recorded at this circuit yet.")

# ── Most successful ──────────────────────────────────────────────────
left, right = st.columns(2)
with left:
    st.markdown("#### Most successful drivers")
    td = profile["top_drivers"]
    if td:
        st.dataframe(pd.DataFrame(td), use_container_width=True, hide_index=True)
    else:
        st.caption("No winners recorded.")
with right:
    st.markdown("#### Most successful constructors")
    tc = profile["top_constructors"]
    if tc:
        st.dataframe(pd.DataFrame(tc), use_container_width=True, hide_index=True)
    else:
        st.caption("No winners recorded.")
