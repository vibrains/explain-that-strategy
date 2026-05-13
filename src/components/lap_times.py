"""Per-lap lap time chart with compound coloring + SC/rain overlays."""
import plotly.graph_objects as go
import streamlit as st

from src.config import TIRE_DATA, TOKENS
from src.utils.charts import apply_chart_theme, add_race_overlays


def render_lap_times(laps, sc_periods_mapped, weather_summary):
    """Render the lap-time chart and return (valid_laps_clean, median_time) for downstream use."""
    st.markdown('<div class="section-head">Lap times</div>', unsafe_allow_html=True)

    valid_laps = laps[laps["LapTime"].notna()].copy()
    valid_laps["LapTimeSec"] = valid_laps["LapTime"].dt.total_seconds()
    median_time = valid_laps["LapTimeSec"].median()
    valid_laps_clean = valid_laps[valid_laps["LapTimeSec"] < median_time * 1.5]

    fig = go.Figure()
    add_race_overlays(fig, sc_periods_mapped, weather_summary, layer="below", show_annotations=True)

    for compound in valid_laps_clean["Compound"].unique():
        cl = valid_laps_clean[valid_laps_clean["Compound"] == compound]
        td = TIRE_DATA.get(compound, TIRE_DATA["MEDIUM"])
        fig.add_trace(go.Scatter(
            x=cl["LapNumber"],
            y=cl["LapTimeSec"],
            mode="markers+lines",
            name=compound,
            marker=dict(
                color=td["color"],
                size=9,
                line=dict(color=TOKENS["ink"], width=1.5),
            ),
            line=dict(color=td["color"], width=2.5),
        ))

    apply_chart_theme(fig, height=420, x_title="Lap", y_title="Lap time (s)")
    st.plotly_chart(fig, use_container_width=True)

    return valid_laps, valid_laps_clean, median_time
