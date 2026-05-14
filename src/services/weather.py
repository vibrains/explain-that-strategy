"""Weather data fetching and summarization."""
import pandas as pd
import streamlit as st


def _as_seconds(val):
    if val is None or pd.isna(val):
        return None
    if isinstance(val, pd.Timedelta):
        return val.total_seconds()
    if isinstance(val, pd.Timestamp):
        return val.timestamp()
    if hasattr(val, "total_seconds"):
        return val.total_seconds()
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def get_weather_per_lap(session, laps_df):
    """Build a dict mapping lap number -> weather dict.

    Each value: {air_temp, track_temp, humidity, rainfall (bool), wind_speed}.
    """
    try:
        wx = session.weather_data
    except Exception:
        return {}

    if wx is None or wx.empty:
        return {}

    driver_counts = laps_df.groupby("Driver")["LapNumber"].count()
    if driver_counts.empty:
        return {}
    ref_driver = driver_counts.idxmax()
    ref_laps = laps_df[laps_df["Driver"] == ref_driver].sort_values("LapNumber")

    wx = wx.copy()
    wx["_sec"] = wx["Time"].apply(_as_seconds)
    wx = wx.dropna(subset=["_sec"]).sort_values("_sec")

    lap_weather = {}
    for _, lap in ref_laps.iterrows():
        lap_num = int(lap["LapNumber"])
        lap_start = _as_seconds(lap.get("LapStartTime"))
        lap_end = _as_seconds(lap.get("Time"))
        if lap_start is None or lap_end is None:
            continue
        window = wx[(wx["_sec"] >= lap_start) & (wx["_sec"] <= lap_end)]
        if window.empty:
            nearest_idx = (wx["_sec"] - lap_end).abs().idxmin()
            window = wx.loc[[nearest_idx]]

        rainfall_val = window["Rainfall"].mean() if "Rainfall" in window else 0
        lap_weather[lap_num] = {
            "air_temp": float(window["AirTemp"].mean()) if "AirTemp" in window else None,
            "track_temp": float(window["TrackTemp"].mean()) if "TrackTemp" in window else None,
            "humidity": float(window["Humidity"].mean()) if "Humidity" in window else None,
            "rainfall": bool(rainfall_val and rainfall_val >= 0.5),
            "wind_speed": float(window["WindSpeed"].mean()) if "WindSpeed" in window else None,
        }
    return lap_weather


def summarize_weather(lap_weather):
    """Return aggregate stats for UI display."""
    if not lap_weather:
        return None
    track_temps = [w["track_temp"] for w in lap_weather.values() if w["track_temp"] is not None]
    air_temps = [w["air_temp"] for w in lap_weather.values() if w["air_temp"] is not None]
    rain_laps = sorted([lap for lap, w in lap_weather.items() if w["rainfall"]])
    humidity = [w["humidity"] for w in lap_weather.values() if w["humidity"] is not None]

    total_laps = len(lap_weather)
    rain_pct = (len(rain_laps) / total_laps * 100) if total_laps else 0
    if rain_pct == 0:
        condition = "Dry"
    elif rain_pct >= 80:
        condition = "Wet"
    else:
        condition = "Mixed"

    rain_windows = []
    for lap in rain_laps:
        if rain_windows and lap == rain_windows[-1][1] + 1:
            rain_windows[-1] = (rain_windows[-1][0], lap)
        else:
            rain_windows.append((lap, lap))

    return {
        "condition": condition,
        "track_temp_min": min(track_temps) if track_temps else None,
        "track_temp_max": max(track_temps) if track_temps else None,
        "track_temp_avg": sum(track_temps) / len(track_temps) if track_temps else None,
        "air_temp_min": min(air_temps) if air_temps else None,
        "air_temp_max": max(air_temps) if air_temps else None,
        "humidity_avg": sum(humidity) / len(humidity) if humidity else None,
        "rain_pct": rain_pct,
        "rain_windows": rain_windows,
    }


@st.cache_data(show_spinner=False)
def cached_weather_data(year: int, gp: str, session_code: str):
    from src.services.fastf1_client import load_session
    session = load_session(year, gp, session_code)
    lap_weather = get_weather_per_lap(session, session.laps)
    weather_summary = summarize_weather(lap_weather)
    return lap_weather, weather_summary
