"""Horizontal stint timeline + inline pit notes."""
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    PIT_STOP_LOSS_NORMAL,
    PIT_STOP_LOSS_SC,
    PIT_STOP_LOSS_VSC,
    TIRE_DATA,
    TOKENS,
)
from src.utils.charts import apply_chart_theme, add_race_overlays


def _render_timeline(actual_stints, total_laps, sc_periods_mapped, weather_summary):
    fig = go.Figure()
    for i, stint in enumerate(actual_stints):
        compound = stint["compound"]
        td = TIRE_DATA.get(compound, TIRE_DATA["MEDIUM"])
        length = stint["end_lap"] - stint["start_lap"] + 1
        fig.add_trace(go.Bar(
            y=["Stints"],
            x=[length],
            base=[stint["start_lap"] - 1],
            orientation="h",
            marker=dict(color=td["color"], line=dict(color=TOKENS["ink"], width=1)),
            name=f"Stint {i+1}",
            text=f"{compound}<br>L{stint['start_lap']}–{stint['end_lap']}",
            textposition="inside",
            textfont=dict(
                color="#FFFFFF" if compound == "HARD" else TOKENS["ink"],
                size=12, family=TOKENS["font_display"],
            ),
            hovertemplate=(
                f"<b>Stint {i+1}: {compound}</b><br>"
                f"Laps {stint['start_lap']}–{stint['end_lap']} ({length} laps)<extra></extra>"
            ),
            showlegend=False,
        ))

    add_race_overlays(fig, sc_periods_mapped, weather_summary, layer="above", show_annotations=True)

    apply_chart_theme(fig, height=130, x_title="Lap")
    fig.update_layout(
        barmode="stack",
        margin=dict(l=10, r=10, t=20, b=30),
        xaxis=dict(range=[0, total_laps + 1], showgrid=False, gridcolor=TOKENS["rule_soft"]),
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_pit_notes(pit_info):
    if not pit_info:
        return
    notes = []
    for pi in pit_info:
        if pi["under_sc"]:
            saved = PIT_STOP_LOSS_NORMAL - (
                PIT_STOP_LOSS_SC if pi["under_sc"] == "SC" else PIT_STOP_LOSS_VSC
            )
            notes.append(
                f"<div class='pit-note'><span class='pit-lap'>Lap {pi['lap']}</span>"
                f"<span class='pit-detail'> · {pi['from_compound'].title()} → "
                f"{pi['to_compound'].title()} under {pi['under_sc']} · saved ~{saved:.0f}s</span></div>"
            )
        else:
            notes.append(
                f"<div class='pit-note'><span class='pit-lap'>Lap {pi['lap']}</span>"
                f"<span class='pit-detail'> · {pi['from_compound'].title()} → "
                f"{pi['to_compound'].title()} · green flag</span></div>"
            )
    st.markdown("".join(notes), unsafe_allow_html=True)


def render_strategy_timeline(actual_stints, pit_info, total_laps,
                             sc_periods_mapped, weather_summary):
    actual_name = " → ".join([s["compound"].title() for s in actual_stints])
    num_stops = len(actual_stints) - 1
    st.markdown(
        f"<div style='margin-top:28px;color:var(--ink-3);font-size:var(--text-sm);'>"
        f"{actual_name} · {num_stops}-stop</div>",
        unsafe_allow_html=True,
    )
    _render_timeline(actual_stints, total_laps, sc_periods_mapped, weather_summary)
    _render_pit_notes(pit_info)
