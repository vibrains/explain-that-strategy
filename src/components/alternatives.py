"""Alternative-strategy simulation + filter + table."""
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from src.config import (
    BASE_TIME_QUANTILE,
    VERDICT_FASTER_THRESHOLD,
    VERDICT_NEUTRAL_RANGE,
)
from src.services.simulation import (
    generate_alt_strategies,
    simulate_strategy,
)
from src.services.strategy import actual_stints_to_sim_format


def compute_base_time(
    valid_laps_clean: pd.DataFrame, sc_periods_mapped: List[Dict[str, Any]]
) -> float:
    """Median pace on non-SC laps, as a clean reference for simulation."""
    non_sc = valid_laps_clean.copy()
    for period in sc_periods_mapped:
        non_sc = non_sc[~non_sc["LapNumber"].between(period["start_lap"], period["end_lap"])]
    if not non_sc.empty:
        return float(non_sc["LapTimeSec"].quantile(BASE_TIME_QUANTILE))
    return float(valid_laps_clean["LapTimeSec"].quantile(BASE_TIME_QUANTILE))


def simulate_all(actual_stints, total_laps, sc_periods_mapped, sc_laps,
                 lap_weather, base_time):
    """Run the actual strategy + all alternatives through the simulator.

    Returns (actual_total, results_df).
    """
    actual_stops, first_compound = actual_stints_to_sim_format(actual_stints)
    if not actual_stops:
        actual_stops = [{"lap": total_laps, "compound": first_compound, "next_compound": first_compound}]
    actual_total, _, _ = simulate_strategy(
        total_laps, base_time, actual_stops, sc_laps, lap_weather,
    )

    alt_strategies = generate_alt_strategies(
        total_laps, actual_stints, sc_periods_mapped, lap_weather,
    )

    rows = []
    for strat in alt_strategies:
        stops = strat["stops"]
        stops[0]["compound"] = strat["first_compound"]
        total, lap_times, _ = simulate_strategy(
            total_laps, base_time, stops, sc_laps, lap_weather,
        )
        delta = total - actual_total
        rows.append({
            "Strategy": strat["name"],
            "Total Time": total,
            "Delta": delta,
            "Stops": len(stops),
            "SC Opportunistic": bool(strat.get("sc_opportunistic")),
            "Weather": bool(strat.get("weather_aware")),
            "lap_times": lap_times,
        })

    return actual_total, pd.DataFrame(rows).sort_values("Delta")


@st.cache_data(show_spinner=False)
def cached_simulate_all(year, gp, session_code, driver_code,
                        actual_stints, total_laps, sc_periods_mapped,
                        sc_laps, lap_weather, base_time):
    return simulate_all(actual_stints, total_laps, sc_periods_mapped,
                        sc_laps, lap_weather, base_time)


def render_alternatives(results_df):
    st.markdown(
        '<div class="section-head">Alternative Strategies'
        '<span class="hint">what if the team had pitted differently</span></div>',
        unsafe_allow_html=True,
    )

    filter_options = ["All", "Safety car plays", "Wet-weather plays", "1-stop", "2-stop", "3-stop"]
    strat_filter = st.radio(
        "Filter alternatives",
        filter_options,
        horizontal=True,
        label_visibility="collapsed",
    )

    if strat_filter == "Safety car plays":
        filtered = results_df[results_df["SC Opportunistic"] == True]
    elif strat_filter == "Wet-weather plays":
        filtered = results_df[results_df["Weather"] == True]
    elif strat_filter == "1-stop":
        filtered = results_df[results_df["Stops"] == 1]
    elif strat_filter == "2-stop":
        filtered = results_df[results_df["Stops"] == 2]
    elif strat_filter == "3-stop":
        filtered = results_df[results_df["Stops"] == 3]
    else:
        filtered = results_df

    if filtered.empty:
        st.caption("No strategies match this filter.")
        return

    top = filtered.head(10).copy()
    display = top[["Strategy", "Delta", "Stops"]].copy()
    display["Delta"] = top["Delta"].apply(lambda x: f"{x:+.1f}s")
    display["Verdict"] = top["Delta"].apply(
        lambda x: (
            "Faster"
            if x < VERDICT_FASTER_THRESHOLD
            else ("Neutral" if abs(x) <= VERDICT_NEUTRAL_RANGE else "Slower")
        )
    )
    st.dataframe(display, use_container_width=True, hide_index=True)
