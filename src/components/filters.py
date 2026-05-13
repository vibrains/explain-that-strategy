"""Top filter row: season, grand prix, session type."""
import streamlit as st

from src.services.fastf1_client import available_seasons, get_event_schedule


def render_filters():
    """Render the season/GP/session selects and return (year, gp, session_code)."""
    col1, col2, col3 = st.columns(3)

    with col1:
        year = st.selectbox("Season", available_seasons())

    with col2:
        try:
            schedule = get_event_schedule(year)
        except Exception as e:
            st.error(
                "Could not load the season schedule. Check your connection and try another "
                "year. If this keeps happening, reload the app."
            )
            st.stop()
        race_names = schedule["EventName"].tolist()
        gp = st.selectbox("Grand Prix", race_names)

    with col3:
        session_type = st.selectbox("Session", ["Race", "Sprint"], index=0)
        session_code = "R" if session_type == "Race" else "S"

    return year, gp, session_code
