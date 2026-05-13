"""Race conditions panel: weather + SC/VSC incidents."""
import streamlit as st

from src.config import PIT_STOP_LOSS_NORMAL, PIT_STOP_LOSS_SC, PIT_STOP_LOSS_VSC


def _render_weather(weather_summary):
    if not weather_summary:
        st.caption("No weather data available.")
        return

    cond = weather_summary["condition"]
    parts = [f"<b style='color:var(--ink);'>{cond}</b>"]
    if weather_summary["track_temp_avg"] is not None:
        parts.append(f"{weather_summary['track_temp_avg']:.0f}° track")
    if weather_summary["air_temp_min"] is not None:
        avg_air = (weather_summary['air_temp_min'] + weather_summary['air_temp_max']) / 2
        parts.append(f"{avg_air:.0f}° air")
    if weather_summary["humidity_avg"] is not None:
        parts.append(f"{weather_summary['humidity_avg']:.0f}% humidity")

    st.markdown(
        "<div style='color:var(--ink-3);font-size:var(--text-sm);margin-bottom:4px;'>Weather</div>"
        f"<div style='font-size:var(--text-base);color:var(--ink-2);'>"
        f"{' · '.join(parts)}</div>",
        unsafe_allow_html=True,
    )
    if weather_summary["rain_windows"]:
        windows_str = ", ".join(
            f"{a}–{b}" if a != b else f"{a}"
            for a, b in weather_summary["rain_windows"]
        )
        st.markdown(
            f"<div style='margin-top:8px;font-size:var(--text-sm);color:var(--ink-3);'>"
            f"Rain on laps {windows_str} · {weather_summary['rain_pct']:.0f}% of race</div>",
            unsafe_allow_html=True,
        )


def _render_incidents(sc_periods_mapped):
    st.markdown(
        "<div style='color:var(--ink-3);font-size:var(--text-sm);margin-bottom:4px;'>Incidents</div>",
        unsafe_allow_html=True,
    )
    if not sc_periods_mapped:
        st.markdown(
            "<div style='color:var(--ink-2);font-size:var(--text-base);padding:10px 0;'>"
            "Green flag race — no safety car periods.</div>",
            unsafe_allow_html=True,
        )
        return

    items = []
    for p in sc_periods_mapped:
        cls = "sc" if p["type"] == "SC" else "vsc"
        saved = PIT_STOP_LOSS_NORMAL - (PIT_STOP_LOSS_SC if p["type"] == "SC" else PIT_STOP_LOSS_VSC)
        items.append(
            f"<li class='{cls}'>"
            f"<span class='dot'></span>"
            f"<span class='ev-title'>{p['type']}, laps {p['start_lap']}–{p['end_lap']}</span>"
            f"<div class='ev-sub'>{p['end_lap'] - p['start_lap'] + 1} laps · "
            f"saves ~{saved:.0f}s if pitting</div>"
            f"</li>"
        )
    st.markdown(f"<ul class='event-list'>{''.join(items)}</ul>", unsafe_allow_html=True)


def render_race_conditions(weather_summary, sc_periods_mapped):
    st.markdown('<div class="section-head">Race Conditions</div>', unsafe_allow_html=True)
    cond_col, sc_col = st.columns([3, 2], gap="large")
    with cond_col:
        _render_weather(weather_summary)
    with sc_col:
        _render_incidents(sc_periods_mapped)
