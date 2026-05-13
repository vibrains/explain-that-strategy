"""Compare an alternative strategy visually against the actual one."""
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    TIRE_DATA,
    TOKENS,
    VERDICT_FASTER_THRESHOLD,
    VERDICT_NEUTRAL_RANGE,
)
from src.utils.charts import apply_chart_theme, add_race_overlays


def render_compare(
    results_df: pd.DataFrame,
    valid_laps_clean: pd.DataFrame,
    sc_periods_mapped: List[Dict[str, Any]],
    weather_summary: Dict[str, Any],
) -> None:
    st.markdown(
        '<div class="section-head">Compare'
        '<span class="hint">pick an alternative to plot against the actual strategy</span></div>',
        unsafe_allow_html=True,
    )

    compare_options = results_df["Strategy"].tolist()
    selected = st.selectbox("Compare with:", compare_options, label_visibility="collapsed")
    if not selected:
        return

    sel_data = results_df[results_df["Strategy"] == selected].iloc[0]
    sel_laps = sel_data["lap_times"]
    delta = sel_data["Delta"]
    verdict = "FASTER" if delta < VERDICT_FASTER_THRESHOLD else (
        "ABOUT THE SAME" if abs(delta) <= VERDICT_NEUTRAL_RANGE else "SLOWER"
    )

    verdict_color = {
        "FASTER": TOKENS["info"],
        "SLOWER": TOKENS["alert"],
        "ABOUT THE SAME": TOKENS["ink_3"],
    }.get(verdict, TOKENS["ink_3"])

    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:12px;margin:14px 0 6px 0;'>"
        f"<div style='font-family:var(--font-display);font-weight:700;text-transform:uppercase;"
        f"font-size:var(--text-base);color:var(--ink);'>{selected}</div>"
        f"<div style='color:{verdict_color};font-size:var(--text-sm);font-weight:600;'>"
        f"{delta:+.1f}s · {verdict.lower()}</div></div>",
        unsafe_allow_html=True,
    )

    fig = go.Figure()
    add_race_overlays(fig, sc_periods_mapped, weather_summary, layer="below", show_annotations=True)

    # Actual lap times.
    for compound in valid_laps_clean["Compound"].unique():
        cl = valid_laps_clean[valid_laps_clean["Compound"] == compound]
        td = TIRE_DATA.get(compound, TIRE_DATA["MEDIUM"])
        fig.add_trace(go.Scatter(
            x=cl["LapNumber"],
            y=cl["LapTimeSec"],
            mode="markers",
            name=f"Actual ({compound})",
            marker=dict(
                color=td["color"],
                size=8,
                line=dict(color=TOKENS["ink"], width=1.5),
            ),
            opacity=0.85,
        ))

    # Simulated alternative.
    sel_df = pd.DataFrame(sel_laps)
    for compound in sel_df["compound"].unique():
        cl = sel_df[sel_df["compound"] == compound]
        td = TIRE_DATA.get(compound, TIRE_DATA["MEDIUM"])
        fig.add_trace(go.Scatter(
            x=cl["lap"],
            y=cl["time"],
            mode="lines",
            name=f"Alt ({compound})",
            line=dict(color=td["color"], width=3, dash="dash"),
        ))

    apply_chart_theme(fig, height=420, x_title="Lap", y_title="Lap time (s)")
    st.plotly_chart(fig, use_container_width=True)

    _render_verdict_line(sel_data, delta)


def _render_verdict_line(sel_data: Dict[str, Any], delta: float) -> None:
    sc_note = ", exploiting a cheap pit window" if sel_data.get("SC Opportunistic") else ""
    if delta < -5:
        msg = f"~{abs(delta):.1f}s faster{sc_note}. The team left time on the table."
    elif delta < VERDICT_FASTER_THRESHOLD:
        msg = f"Marginally faster by {abs(delta):.1f}s{sc_note}."
    elif abs(delta) <= VERDICT_NEUTRAL_RANGE:
        msg = "Within a second either way — the team called it right."
    elif delta < 5:
        msg = f"{delta:.1f}s slower. Team made the right call."
    else:
        msg = f"{delta:.1f}s slower — would have been a clear mistake."

    st.markdown(
        f"<div style='padding:12px 0;color:var(--ink-2);font-size:var(--text-base);'>{msg}</div>",
        unsafe_allow_html=True,
    )
