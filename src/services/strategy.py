"""Actual-strategy extraction from lap data."""
from typing import Any, Dict, List, Optional, Tuple

import fastf1
import pandas as pd

from src.config import VALID_COMPOUNDS


def get_driver_strategy(
    session: fastf1.core.Session, driver: str
) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    """Extract a driver's stints (compound + lap range) from the session laps.

    Args:
        session: FastF1 session object containing lap data.
        driver: Driver abbreviation (e.g., "HAM", "VER").

    Returns:
        Tuple of (stints list, laps DataFrame). Stints is a list of dictionaries
        with keys: 'compound', 'start_lap', 'end_lap'.
    """
    laps = session.laps.pick_drivers(driver).sort_values("LapNumber")
    if laps.empty:
        return [], pd.DataFrame()

    stints: List[Dict[str, Any]] = []
    current_compound: Optional[str] = None
    stint_start: Optional[int] = None

    for _, lap in laps.iterrows():
        compound = lap["Compound"]
        if compound != current_compound:
            if current_compound is not None:
                stints.append({
                    "compound": current_compound,
                    "start_lap": stint_start,
                    "end_lap": int(lap["LapNumber"]) - 1,
                })
            current_compound = compound
            stint_start = int(lap["LapNumber"])

    if current_compound is not None:
        stints.append({
            "compound": current_compound,
            "start_lap": stint_start,
            "end_lap": int(laps["LapNumber"].max()),
        })

    return stints, laps


def detect_pit_laps_under_sc(
    actual_stints: List[Dict[str, Any]], sc_laps: Dict[int, str]
) -> List[Dict[str, Any]]:
    """For each pit stop (gap between consecutive stints), note if it fell under SC/VSC.

    Args:
        actual_stints: List of stint dictionaries with 'compound', 'start_lap', 'end_lap'.
        sc_laps: Dictionary mapping lap number to 'SC' or 'VSC'.

    Returns:
        List of pit stop dictionaries with keys: 'lap', 'from_compound',
        'to_compound', 'under_sc'.
    """
    pit_info: List[Dict[str, Any]] = []
    for i in range(len(actual_stints) - 1):
        pit_lap = actual_stints[i]["end_lap"]
        pit_info.append({
            "lap": pit_lap,
            "from_compound": actual_stints[i]["compound"],
            "to_compound": actual_stints[i + 1]["compound"],
            "under_sc": sc_laps.get(pit_lap, None),
        })
    return pit_info


def actual_stints_to_sim_format(
    stints: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], str]:
    """Convert stint list to the (stops, first_compound) shape simulate_strategy expects.

    Args:
        stints: List of stint dictionaries with 'compound', 'start_lap', 'end_lap'.

    Returns:
        Tuple of (stops list, first_compound string). Stops list contains
        dictionaries with keys: 'lap', 'compound', 'next_compound'.
    """
    if len(stints) <= 1:
        return [], stints[0]["compound"] if stints else "MEDIUM"

    stops: List[Dict[str, Any]] = []
    for i in range(len(stints) - 1):
        stops.append({
            "lap": stints[i]["end_lap"],
            "compound": stints[i]["compound"],
            "next_compound": stints[i + 1]["compound"],
        })
    return stops, stints[0]["compound"]
