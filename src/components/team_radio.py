"""Team-radio expander with lap-context tags."""
import streamlit as st

from src.services.team_radio import fetch_team_radio, map_radio_to_laps


def _lap_context_tags(lap, sc_laps, pit_info, lap_weather):
    if lap is None:
        return ""
    tags = []
    sc_type = sc_laps.get(lap)
    if sc_type:
        cls = "tag-sc" if sc_type == "SC" else "tag-vsc"
        tags.append(f"<span class='tag {cls}'>{sc_type}</span>")
    for pi in pit_info:
        if abs(pi["lap"] - lap) <= 1:
            tags.append(
                f"<span class='tag'>Pit {pi['from_compound'][:1]}→{pi['to_compound'][:1]}</span>"
            )
    if lap_weather.get(lap, {}).get("rainfall"):
        tags.append("<span class='tag tag-rain'>Rain</span>")
    return " ".join(tags)


def render_team_radio(session, driver_code, sc_laps, pit_info, lap_weather):
    session_path = None
    try:
        session_path = session.session_info.get("Path")
    except Exception:
        session_path = None

    radio_clips = fetch_team_radio(session_path) if session_path else []
    driver_radio = map_radio_to_laps(radio_clips, session, session.laps, driver_code)

    if not driver_radio:
        return

    st.markdown(
        '<div class="section-head">Team Radio'
        '<span class="hint">driver-to-engineer audio clips tagged by lap</span></div>',
        unsafe_allow_html=True,
    )

    with st.expander(f"{len(driver_radio)} clips", expanded=False):
        if not driver_radio:
            st.caption("No team radio clips found for this driver.")
            return

        for clip in driver_radio:
            lap_label = (
                f"Lap {clip['lap']}" if clip["lap"]
                else f"Pre-race · {clip['timestamp_sec']/60:.1f} min"
            )
            ctx = _lap_context_tags(clip["lap"], sc_laps, pit_info, lap_weather)
            st.markdown(
                f"<div style='margin-top:8px;'>"
                f"<span style='font-weight:600;'>{lap_label}</span> {ctx}"
                f"</div>",
                unsafe_allow_html=True,
            )
            try:
                st.audio(clip["audio_url"])
            except Exception:
                st.caption(f"[Audio unavailable]({clip['audio_url']})")
