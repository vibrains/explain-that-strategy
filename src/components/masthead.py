"""Editorial race masthead at the top of the analysis."""
import pandas as pd
import streamlit as st

from src.utils.assets import f1_logo


def render_masthead(session, year, gp, session_code):
    event_name = gp
    try:
        event = getattr(session, "event", None)
        if event is not None and hasattr(event, "get"):
            event_name = event.get("EventName", gp)
    except Exception:
        pass

    event_date = ""
    try:
        if session.date is not None:
            event_date = pd.Timestamp(session.date).strftime("%d %B %Y")
    except Exception:
        event_date = ""

    session_label = "Race" if session_code == "R" else "Sprint"
    meta = session_label + (f" · {event_date}" if event_date else "")

    st.markdown(
        f"""
        <div class="race-masthead">
            <div class="eyebrow">
                <span>{year}</span>
                <span class="sep">·</span>
                {f1_logo("f1-mark f1-mark--eyebrow")}
            </div>
            <h2>{event_name}</h2>
            <div class="meta">{meta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
