"""Explain That Strategy — F1 tire-strategy simulator.

Entry point. Wires together filters → masthead → qualifying → results table → driver analysis.
Business logic lives in `src/services/`, UI pieces in `src/components/`.
"""
import logging

import streamlit as st

from src.components.alternatives import cached_simulate_all, compute_base_time, render_alternatives
from src.components.compare import render_compare
from src.components.driver_summary import render_driver_summary
from src.components.lap_times import render_lap_times
from src.components.masthead import render_masthead
from src.components.qualifying_results import render_qualifying_results
from src.components.race_conditions import render_race_conditions
from src.components.results_table import render_results_table
from src.components.strategy_timeline import render_strategy_timeline
from src.components.styles import inject_styles
from src.components.team_radio import render_team_radio
from src.components.verdict import render_verdict
from src.config import APP_NAME
from src.logging_config import setup_logging
from src.services.fastf1_client import available_seasons, get_event_schedule, init_cache, load_session, load_session_light
from src.services.safety_car import cached_sc_periods_mapped, get_sc_laps_set
from src.services.strategy import detect_pit_laps_under_sc, get_driver_strategy
from src.services.weather import cached_weather_data
from src.state import reset_selection_on_race_change
from src.utils.assets import f1_logo

# Initialize logging
logger = setup_logging(level=logging.INFO)


def main():
    st.set_page_config(page_title=APP_NAME, page_icon="🏎️", layout="centered")
    init_cache()
    inject_styles()

    st.markdown(
        f"""
        <div class="app-title">
            {f1_logo("f1-mark f1-mark--title")}
            <h1>{APP_NAME}</h1>
        </div>
        <p class="app-subtitle">
            Break down pit stops, tire strategies, safety car calls, and
            weather crossovers from every Formula 1 race since 2018 —
            then simulate the alternatives the team didn't take.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ── 1. Read current filter values from session state (or defaults) ──
    year_list = available_seasons()
    year = st.session_state.get("filter_year", year_list[0])
    if year not in year_list:
        year = year_list[0]

    try:
        schedule = get_event_schedule(year)
    except Exception as e:
        st.error(
            "Could not load the season schedule. Check your connection and try another "
            "year. If this keeps happening, reload the app."
        )
        st.stop()

    race_names = schedule["EventName"].tolist()
    gp = st.session_state.get("filter_gp", race_names[0] if race_names else "")
    if gp not in race_names:
        gp = race_names[0] if race_names else ""

    session_type = st.session_state.get("filter_session", "Race")
    session_code = "R" if session_type == "Race" else "S"

    # Detect race change and clear stale dataframe selection state.
    race_key = (year, gp, session_code)
    reset_selection_on_race_change(race_key)

    # ── 2. Fast session load — results only (no laps/weather/messages) ──
    logger.info(f"Loading session: {year} {gp} ({session_code})")
    session = None
    try:
        session = load_session_light(year, gp, session_code)
        logger.info(f"Loaded session metadata for {year} {gp}")
    except Exception as e:
        logger.error(f"Failed to load session: {e}")

    # ── 3. Render 4-column filter bar (Season | GP | Session | Driver) ──
    with st.container(key="filter-bar"):
        cols = st.columns(4)

        with cols[0]:
            year = st.selectbox(
                "Season", year_list,
                index=year_list.index(year),
                key="filter_year",
            )

        with cols[1]:
            schedule = get_event_schedule(year)
            race_names = schedule["EventName"].tolist()
            gp_idx = race_names.index(gp) if gp in race_names else 0
            gp = st.selectbox(
                "Grand Prix", race_names,
                index=gp_idx,
                key="filter_gp",
            )

        with cols[2]:
            session_options = ["Race", "Sprint"]
            session_idx = 0 if session_code == "R" else 1
            session_type = st.selectbox(
                "Session", session_options,
                index=session_idx,
                key="filter_session",
            )
            session_code = "R" if session_type == "Race" else "S"

        with cols[3]:
            if session is not None and session.results is not None and not session.results.empty:
                results_sorted = (
                    session.results
                    .sort_values("Position", na_position="last")
                    .reset_index(drop=True)
                )
                driver_options = []
                driver_codes = []
                for _, r in results_sorted.iterrows():
                    abbrev = r.get("Abbreviation", "")
                    name = r.get("FullName", "") or abbrev
                    driver_options.append(f"{name} ({abbrev})")
                    driver_codes.append(abbrev)

                preferred = st.session_state.get("_preferred_driver")
                driver_idx = None
                if preferred and preferred in driver_codes:
                    driver_idx = driver_codes.index(preferred)

                selected_label = st.selectbox(
                    "Driver", driver_options,
                    index=driver_idx,
                    placeholder="Select Driver",
                    key="filter_driver",
                )
                if selected_label is None:
                    driver_code = None
                else:
                    driver_code = driver_codes[driver_options.index(selected_label)]
                    st.session_state["_preferred_driver"] = driver_code
                    # Track driver changes so we can scroll to the summary after it renders.
                    if st.session_state.get("_last_driver_filter") != driver_code:
                        st.session_state["_last_driver_filter"] = driver_code
                        st.session_state["_scroll_to_driver"] = True
            else:
                st.selectbox("Driver", ["—"], disabled=True, key="filter_driver_placeholder")
                driver_code = None

    if session is None:
        st.error(
            "Race data isn't available yet for this event. "
            "Try selecting a completed race or an earlier season."
        )
        st.stop()

    if driver_code is None:
        st.markdown(
            """
            <style>
            .st-key-filter-bar .st-key-filter_driver div[data-baseweb="select"] > div,
            .st-key-filter-bar .st-key-filter_driver_placeholder div[data-baseweb="select"] > div {
                animation: pulse-border 2s ease-in-out infinite;
                border-color: var(--accent) !important;
                border-radius: 8px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        render_masthead(session, year, gp, session_code)
        render_results_table(session, "")
        st.info(
            "Pick a driver from the **Driver** dropdown above to explore their "
            "tire strategy, lap-by-lap pace, pit stop timing, team radio, and "
            "simulated alternative strategies."
        )
        st.stop()

    # ── 4. Full session load — laps, weather, messages (deferred until driver selected) ──
    try:
        session = load_session(year, gp, session_code)
        logger.info(f"Loaded full session with {len(session.laps)} laps")
    except Exception as e:
        logger.error(f"Failed to load full session: {e}")
        st.error(
            "Race data isn't available yet for this event. "
            "Try selecting a completed race or an earlier season."
        )
        st.stop()

    sc_periods_mapped = cached_sc_periods_mapped(year, gp, session_code)
    sc_laps = get_sc_laps_set(sc_periods_mapped)
    lap_weather, weather_summary = cached_weather_data(year, gp, session_code)

    # ── 5. Masthead ──
    render_masthead(session, year, gp, session_code)

    # ── 6. Qualifying results (optional) ──
    render_qualifying_results(year, gp, session)

    # ── 7. Results table (read-only, no checkboxes) ──
    selected_idx, driver_code, sorted_results = render_results_table(session, driver_code)
    logger.info(f"Selected driver: {driver_code}")

    # ── 8. Driver summary + race conditions ──
    render_driver_summary(sorted_results.iloc[selected_idx], driver_code)

    # Auto-scroll to the driver summary when the driver filter changed.
    # st.markdown strips <script>, so use components.html (iframe). The nonce
    # forces Streamlit to treat each rerun as a fresh component so the script
    # re-executes; the retry loop beats Streamlit's own scroll restoration.
    if st.session_state.pop("_scroll_to_driver", False):
        import time
        import streamlit.components.v1 as components
        nonce = f"{driver_code}-{int(time.time() * 1000)}"
        components.html(
            f"""
            <div data-nonce="{nonce}" style="display:none"></div>
            <script>
              (function(){{
                var win = window.parent;
                var doc = win.document;
                var cancelled = false;
                function onUserScroll(){{ cancelled = true; }}
                // Only user-initiated wheel/touch/key events should cancel;
                // our own programmatic scrollIntoView must not.
                win.addEventListener('wheel', onUserScroll, {{passive:true, once:true}});
                win.addEventListener('touchmove', onUserScroll, {{passive:true, once:true}});
                win.addEventListener('keydown', onUserScroll, {{once:true}});
                function scrollOnce(){{
                  if (cancelled) return;
                  var el = doc.getElementById('driver-summary');
                  if (el) el.scrollIntoView({{behavior:'smooth', block:'start'}});
                }}
                // Two fires: first to move, second to re-assert after Streamlit
                // settles layout. Then we stop so the user can scroll freely.
                setTimeout(scrollOnce, 150);
                setTimeout(scrollOnce, 600);
              }})();
            </script>
            """,
            height=0,
        )

    render_race_conditions(weather_summary, sc_periods_mapped)

    # ── 9. Actual strategy ──
    actual_stints, laps = get_driver_strategy(session, driver_code)
    if not actual_stints:
        logger.warning(f"No lap data found for driver {driver_code}")
        st.warning("No lap data found for this driver.")
        return
    logger.info(f"Found {len(actual_stints)} stints for {driver_code}")

    total_laps = int(laps["LapNumber"].max())
    pit_info = detect_pit_laps_under_sc(actual_stints, sc_laps)

    render_strategy_timeline(
        actual_stints, pit_info, total_laps,
        sc_periods_mapped, weather_summary,
    )

    # ── 10. Lap times, team radio, simulation ──
    valid_laps, valid_laps_clean, _ = render_lap_times(
        laps, sc_periods_mapped, weather_summary,
    )
    render_team_radio(session, driver_code, sc_laps, pit_info, lap_weather,
                      year, gp, session_code)

    base_time = compute_base_time(valid_laps_clean, sc_periods_mapped)
    _, results_df = cached_simulate_all(
        year, gp, session_code, driver_code,
        actual_stints, total_laps, sc_periods_mapped, sc_laps, lap_weather, base_time,
    )
    render_alternatives(results_df)
    render_compare(results_df, valid_laps_clean, sc_periods_mapped, weather_summary)
    render_verdict(results_df)


if __name__ == "__main__":
    main()
