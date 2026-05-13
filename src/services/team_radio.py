"""Team radio fetching + lap mapping.

FastF1 doesn't wrap the F1 live timing TeamRadio.json feed, so we fetch it directly.
"""
import json

import pandas as pd
import requests
import streamlit as st


@st.cache_data(show_spinner="Tuning into team radio")
def fetch_team_radio(session_path):
    """Fetch the TeamRadio.json manifest and return a list of clips.

    Each clip: {utc, racing_number, audio_url}.
    """
    if not session_path:
        return []
    url = f"https://livetiming.formula1.com/static/{session_path}TeamRadio.json"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except Exception:
        return []
    try:
        data = json.loads(r.content.decode("utf-8-sig"))
    except Exception:
        return []
    captures = data.get("Captures", []) if isinstance(data, dict) else []
    base = f"https://livetiming.formula1.com/static/{session_path}"
    return [
        {
            "utc": c.get("Utc"),
            "racing_number": str(c.get("RacingNumber", "")),
            "audio_url": base + c.get("Path", ""),
        }
        for c in captures
        if c.get("Path")
    ]


def map_radio_to_laps(radio_clips, session, laps_df, driver_code):
    """Filter clips to one driver and tag each with the lap they fell within."""
    if not radio_clips:
        return []

    results = session.results
    driver_number = None
    if results is not None and not results.empty:
        row = results[results["Abbreviation"] == driver_code]
        if not row.empty:
            driver_number = str(row.iloc[0].get("DriverNumber", "")).strip()
    if not driver_number:
        return []

    driver_clips = [c for c in radio_clips if c["racing_number"] == driver_number]
    if not driver_clips:
        return []

    session_start = getattr(session, "t0_date", None) or getattr(session, "date", None)
    if session_start is None:
        return []
    session_start = pd.Timestamp(session_start)
    if session_start.tzinfo is None:
        session_start = session_start.tz_localize("UTC")

    ref_laps = laps_df[laps_df["Driver"] == driver_code].sort_values("LapNumber")
    if ref_laps.empty:
        return []

    mapped = []
    for c in driver_clips:
        try:
            utc = pd.Timestamp(c["utc"])
            if utc.tzinfo is None:
                utc = utc.tz_localize("UTC")
            rel_sec = (utc - session_start).total_seconds()
        except Exception:
            continue

        lap_num = None
        for _, lap in ref_laps.iterrows():
            lap_start = lap.get("LapStartTime")
            lap_end = lap.get("Time")
            if pd.isna(lap_start) or pd.isna(lap_end):
                continue
            ls = lap_start.total_seconds() if isinstance(lap_start, pd.Timedelta) else None
            le = lap_end.total_seconds() if isinstance(lap_end, pd.Timedelta) else None
            if ls is None or le is None:
                continue
            if ls <= rel_sec <= le:
                lap_num = int(lap["LapNumber"])
                break

        mapped.append({
            "lap": lap_num,
            "timestamp_sec": rel_sec,
            "audio_url": c["audio_url"],
            "utc": c["utc"],
        })

    mapped.sort(key=lambda x: x["timestamp_sec"])
    return mapped
