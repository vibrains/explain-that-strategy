"""FastF1 session + schedule loaders."""
import os
from datetime import datetime
from typing import List

import fastf1
import pandas as pd
import streamlit as st

from src.config import CACHE_DIR


def init_cache() -> None:
    """Enable FastF1's local cache. Call once at app startup."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)


def available_seasons() -> List[int]:
    """Return list of available seasons (newest first).

    Returns:
        List of years from the current year down to 2018.
    """
    latest_year = max(datetime.now().year, 2018)
    return list(range(latest_year, 2017, -1))


@st.cache_data(show_spinner="Lights out — pulling race data")
def load_session(year: int, gp: str, session_type: str = "R") -> fastf1.core.Session:
    """Load a FastF1 session with caching.

    Args:
        year: Race season year.
        gp: Grand Prix name or round number.
        session_type: Session code ('R' for Race, 'S' for Sprint).

    Returns:
        Loaded FastF1 session object.

    Raises:
        ValueError: If year or gp is invalid.
        Exception: If FastF1 fails to load the session.
    """
    if not isinstance(year, int) or year < 2018:
        raise ValueError(f"year must be an integer >= 2018, got {year}")
    if not gp or not isinstance(gp, str):
        raise ValueError(f"gp must be a non-empty string, got {gp}")

    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False)
    # session.load() silently warns instead of raising when data is unavailable.
    # Probe .laps to surface the DataNotLoadedError early.
    _ = session.laps
    return session


@st.cache_data(show_spinner="Reviewing the season schedule")
def get_event_schedule(year: int) -> pd.DataFrame:
    """Get the event schedule for a season.

    Args:
        year: Season year.

    Returns:
        DataFrame of events with EventFormat set.

    Raises:
        ValueError: If year is invalid.
        Exception: If FastF1 fails to fetch the schedule.
    """
    if not isinstance(year, int) or year < 2018:
        raise ValueError(f"year must be an integer >= 2018, got {year}")

    schedule = fastf1.get_event_schedule(year)
    schedule = schedule[schedule["EventFormat"].notna()]
    # Hide pre-season testing events — no race data is available for them.
    schedule = schedule[schedule["EventFormat"].str.lower() != "testing"]
    return schedule
