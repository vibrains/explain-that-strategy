"""Read-only results table.

Driver selection is handled upstream by the filter dropdown. This component
simply renders the finishing order for the active race.
"""
import pandas as pd
import streamlit as st

from src.config import TOKENS
from src.utils.formatting import format_time_or_gap


def _build_display_df(results):
    sorted_results = results.sort_values("Position", na_position="last").reset_index(drop=True)
    rows = []
    for _, r in sorted_results.iterrows():
        classified = r.get("ClassifiedPosition")
        position = r.get("Position")
        status = r.get("Status", "") or ""
        pos_raw = classified if pd.notna(classified) and str(classified).strip() else (
            str(int(position)) if pd.notna(position) else "—"
        )
        is_winner = str(pos_raw) == "1"
        rows.append({
            "Pos": str(pos_raw),
            "Photo": r.get("HeadshotUrl") or "",
            "Driver": r.get("FullName") or r.get("Abbreviation") or "",
            "Team": r.get("TeamName") or "",
            "No.": str(int(r["DriverNumber"])) if pd.notna(r.get("DriverNumber")) else "",
            "Time / Gap": format_time_or_gap(is_winner, r.get("Time"), status),
            "Pts": f"{r.get('Points', 0):g}" if pd.notna(r.get("Points")) else "0",
            "Status": status if not (isinstance(status, str) and status.startswith("+")) else "Finished",
            "_abbrev": r.get("Abbreviation", ""),
            "_team_color": (
                f"#{r.get('TeamColor')}"
                if pd.notna(r.get("TeamColor")) and r.get("TeamColor")
                else TOKENS["ink_4"]
            ),
        })
    return pd.DataFrame(rows), sorted_results


def render_results_table(session, driver_code):
    """Render the results grid (read-only) for the already-selected driver.

    Args:
        session: Loaded FastF1 session.
        driver_code: Three-letter driver abbreviation selected via the filter.

    Returns:
        (selected_idx, driver_code, sorted_results)
    """
    st.markdown(
        '<div class="section-head">Results<span class="hint">finishing order</span></div>',
        unsafe_allow_html=True,
    )

    results = session.results
    if results is None or results.empty:
        st.error(
            "No results available for this session. If the race was canceled or the "
            "session data is still publishing, pick another event or try again soon."
        )
        st.stop()

    results_display, sorted_results = _build_display_df(results)

    # Find the row index matching the selected driver.
    matches = results_display.index[results_display["_abbrev"] == driver_code].tolist()
    selected_idx = int(matches[0]) if matches else 0
    driver_code = results_display.iloc[selected_idx]["_abbrev"]
    if not driver_code:
        st.stop()

    # Per-row styling — team color on the Team cell.
    def row_style(row):
        color = row["_team_color"]
        return [
            f"color: {color}; font-weight: 600;" if col == "Team" else ""
            for col in results_display.columns
        ]

    styled = results_display.style.apply(row_style, axis=1)

    visible_cols = ["Pos", "Photo", "Driver", "Team", "No.", "Time / Gap", "Pts", "Status"]
    st.dataframe(
        styled,
        hide_index=True,
        column_order=visible_cols,
        height=750,
        column_config={
            "Pos":        st.column_config.TextColumn("POS",        width="small"),
            "Photo":      st.column_config.ImageColumn(" ",          width="small", help="Driver"),
            "Driver":     st.column_config.TextColumn("DRIVER",     width="medium"),
            "Team":       st.column_config.TextColumn("TEAM",       width="medium"),
            "No.":        st.column_config.TextColumn("NO.",        width="small"),
            "Time / Gap": st.column_config.TextColumn("TIME / GAP", width="medium"),
            "Pts":        st.column_config.TextColumn("PTS",        width="small"),
            "Status":     st.column_config.TextColumn("STATUS",     width="small"),
            "_abbrev": None,
            "_team_color": None,
        },
    )

    return selected_idx, driver_code, sorted_results
