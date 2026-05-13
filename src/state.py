"""Session-state management."""
import streamlit as st


def reset_selection_on_race_change(race_key):
    """When the filters change, drop Streamlit's cached widget selection (it
    holds stale row indices for the previous race's results).

    We deliberately keep `_preferred_driver` (the driver's abbreviation) so
    render_results_table can re-apply the same driver in the new race's
    results if they participated.
    """
    if st.session_state.get("_race_key") != race_key:
        st.session_state["_race_key"] = race_key
        st.session_state.pop("results_selection", None)
