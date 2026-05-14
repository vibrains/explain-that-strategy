"""Detect Safety Car and VSC periods from FastF1 session data."""
import pandas as pd
import streamlit as st


def detect_sc_periods(session):
    """Detect SC/VSC periods from track_status (authoritative, session-relative times).

    FastF1 codes: 1=AllClear, 2=Yellow, 4=SC, 5=Red, 6=VSC deployed, 7=VSC ending.
    """
    try:
        ts = session.track_status
    except Exception:
        ts = None

    periods = []

    if ts is not None and not ts.empty:
        current = None
        for _, row in ts.iterrows():
            status = str(row.get("Status", "")).strip()
            time = row.get("Time")

            if status == "4":
                if current is None:
                    current = {"type": "SC", "start_time": time}
                elif current["type"] != "SC":
                    current["end_time"] = time
                    periods.append(current)
                    current = {"type": "SC", "start_time": time}
            elif status == "6":
                if current is None:
                    current = {"type": "VSC", "start_time": time}
                elif current["type"] != "VSC":
                    current["end_time"] = time
                    periods.append(current)
                    current = {"type": "VSC", "start_time": time}
            elif status in ("1", "7"):
                if current is not None:
                    current["end_time"] = time
                    periods.append(current)
                    current = None

        if current is not None:
            current["end_time"] = ts["Time"].iloc[-1]
            periods.append(current)

    # Fallback: parse race_control_messages if track_status is empty.
    if not periods:
        try:
            rcm = session.race_control_messages
        except Exception:
            return []
        if rcm is None or rcm.empty:
            return []

        current = None
        for _, msg in rcm.iterrows():
            cat = msg.get("Category", "")
            message = msg.get("Message", "") or ""
            time = msg.get("Time")
            if cat != "SafetyCar":
                continue
            if "VIRTUAL SAFETY CAR DEPLOYED" in message:
                current = {"type": "VSC", "start_time": time}
            elif "SAFETY CAR DEPLOYED" in message and "VIRTUAL" not in message:
                current = {"type": "SC", "start_time": time}
            elif ("SAFETY CAR IN" in message or "ENDING" in message) and current:
                current["end_time"] = time
                periods.append(current)
                current = None
        if current:
            current["end_time"] = rcm["Time"].max()
            periods.append(current)

    return periods


def _as_seconds(val):
    if isinstance(val, pd.Timedelta):
        return val.total_seconds()
    if isinstance(val, pd.Timestamp):
        return val.timestamp()
    if hasattr(val, "total_seconds"):
        return val.total_seconds()
    return float(val)


def map_sc_periods_to_laps(sc_periods, laps_df, driver=None):
    """Convert SC time periods to lap ranges using a reference driver's lap timing."""
    if not sc_periods:
        return []

    if driver:
        ref_laps = laps_df[laps_df["Driver"] == driver].sort_values("LapNumber")
    else:
        driver_counts = laps_df.groupby("Driver")["LapNumber"].count()
        best_driver = driver_counts.idxmax()
        ref_laps = laps_df[laps_df["Driver"] == best_driver].sort_values("LapNumber")

    if ref_laps.empty:
        return []

    mapped = []
    for period in sc_periods:
        start_time = period["start_time"]
        end_time = period["end_time"]
        start_lap = None
        end_lap = None

        for _, lap in ref_laps.iterrows():
            lap_start = lap.get("LapStartTime")
            lap_end = lap.get("Time")
            lap_num = int(lap["LapNumber"])
            if lap_start is None or lap_end is None:
                continue
            if pd.isna(lap_start) or pd.isna(lap_end):
                continue

            try:
                le_sec = _as_seconds(lap_end)
                ls_sec = _as_seconds(lap_start)
                st_sec = _as_seconds(start_time)
                et_sec = _as_seconds(end_time)
                if start_lap is None and le_sec >= st_sec:
                    start_lap = lap_num
                if ls_sec <= et_sec:
                    end_lap = lap_num
            except (TypeError, ValueError):
                continue

        if start_lap and end_lap:
            mapped.append({
                "type": period["type"],
                "start_lap": start_lap,
                "end_lap": end_lap,
            })

    return mapped


def get_sc_laps_set(sc_periods_mapped):
    """Return {lap_number: 'SC'|'VSC'} for every lap covered by an SC/VSC period."""
    sc_laps = {}
    for p in sc_periods_mapped:
        for lap in range(p["start_lap"], p["end_lap"] + 1):
            sc_laps[lap] = p["type"]
    return sc_laps


@st.cache_data(show_spinner=False)
def cached_sc_periods_mapped(year: int, gp: str, session_code: str):
    from src.services.fastf1_client import load_session
    session = load_session(year, gp, session_code)
    periods = detect_sc_periods(session)
    return map_sc_periods_to_laps(periods, session.laps)
