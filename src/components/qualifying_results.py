"""Qualifying results — horizontal bar chart of fastest-lap deltas from pole."""
import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import TOKENS
from src.services.fastf1_client import load_session
from src.utils.charts import apply_chart_theme

logger = logging.getLogger(__name__)


def _get_team_color_fastest_laps(q_session) -> pd.DataFrame:
    """Build a DataFrame of each driver's fastest qualifying lap with team colors.

    Returns columns: Driver, FullName, Team, TeamColor, LapTime, LapTimeDelta.
    Sorted by LapTime ascending (pole first).
    """
    if q_session.laps is None or q_session.laps.empty:
        return pd.DataFrame()

    drivers = pd.unique(q_session.laps["Driver"])
    fastest_laps = []
    for drv in drivers:
        drv_laps = q_session.laps.pick_drivers(drv)
        if drv_laps.empty:
            continue
        fastest = drv_laps.pick_fastest()
        if fastest is None or fastest.empty:
            continue
        fastest_laps.append(fastest)

    if not fastest_laps:
        return pd.DataFrame()

    df = pd.DataFrame(fastest_laps).sort_values(by="LapTime").reset_index(drop=True)

    # Compute delta from pole
    pole_lap = df.iloc[0]
    df["LapTimeDelta"] = df["LapTime"] - pole_lap["LapTime"]

    return df


def _build_team_colors(df, driver_color_map: dict) -> list:
    """Return a list of hex color strings aligned with df rows.

    Args:
        df: Qualifying fastest-laps DataFrame (must contain 'Driver' column).
        driver_color_map: Mapping of driver abbreviation -> hex color string.
    """
    colors = []
    for _, row in df.iterrows():
        drv = row.get("Driver", "")
        color = driver_color_map.get(drv)
        if color:
            colors.append(color)
        else:
            # Last resort fallback — use FastF1 plotting API
            try:
                import fastf1.plotting
                tc = fastf1.plotting.get_team_color(row.get("Team", ""), session=None)
                colors.append(tc)
            except Exception:
                colors.append(TOKENS["ink_4"])
    return colors


def _format_delta(td) -> str:
    """Format a timedelta delta as +MM:SS.mmm for display."""
    if pd.isna(td):
        return ""
    total_seconds = td.total_seconds()
    sign = "+" if total_seconds > 0 else ""
    minutes = int(abs(total_seconds)) // 60
    seconds = abs(total_seconds) - minutes * 60
    return f"{sign}{minutes:02d}:{seconds:06.3f}"


def _format_laptime(td) -> str:
    """Format an absolute lap time as MM:SS.mmm (no sign)."""
    if pd.isna(td):
        return ""
    total_seconds = td.total_seconds()
    minutes = int(total_seconds) // 60
    seconds = total_seconds - minutes * 60
    return f"{minutes:01d}:{seconds:06.3f}"


def render_qualifying_results(year: int, gp: str, race_session):
    """Render the qualifying results chart above the race results.

    Loads the 'Q' session for the same event and shows a horizontal bar chart
    of each driver's fastest lap delta from pole position, colored by team.

    Args:
        year: Season year.
        gp: Grand Prix name.
        race_session: The already-loaded race session whose ``results`` table
            is used to map driver abbreviations to team colors.
    """
    try:
        q_session = load_session(year, gp, "Q")
    except Exception as e:
        logger.warning(f"Qualifying session not available for {year} {gp}: {e}")
        return

    try:
        df = _get_team_color_fastest_laps(q_session)
    except Exception as e:
        logger.warning(f"Qualifying lap data not available for {year} {gp}: {e}")
        return
    if df.empty:
        logger.info(f"No qualifying laps found for {year} {gp}")
        return

    # Build driver -> team-color lookup from the race results (same source as the
    # results table uses) so bars match the exact team colors shown downstream.
    driver_color_map = {}
    if race_session.results is not None and not race_session.results.empty:
        for _, r in race_session.results.iterrows():
            abbrev = r.get("Abbreviation")
            tc = r.get("TeamColor")
            if pd.notna(abbrev) and pd.notna(tc) and tc:
                hex_color = f"#{tc}" if not str(tc).startswith("#") else str(tc)
                driver_color_map[str(abbrev)] = hex_color

    team_colors = _build_team_colors(df, driver_color_map)
    pole_time_str = _format_laptime(df.iloc[0]["LapTime"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=list(range(len(df))),
        x=df["LapTimeDelta"].dt.total_seconds(),
        orientation="h",
        marker=dict(color=team_colors, line=dict(width=0)),
        text=[_format_delta(d) for d in df["LapTimeDelta"]],
        textposition="outside",
        textfont=dict(family=TOKENS["font_display"], color=TOKENS["ink"], size=13),
        cliponaxis=False,
        hovertemplate=(
            "<b>%{customdata[0]}</b> — %{customdata[1]}<br>"
            "Delta: %{text}<extra></extra>"
        ),
        customdata=[[drv, team] for drv, team in zip(df["Driver"], df.get("Team", ""))],
        showlegend=False,
    ))

    apply_chart_theme(fig, height=min(560, max(380, len(df) * 26)), x_title="Gap to Pole (seconds)")
    fig.update_layout(
        margin=dict(l=10, r=120, t=28, b=40),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(len(df))),
            ticktext=[
                f"{i+1}.  {drv}"
                for i, drv in enumerate(df["Driver"])
            ],
            autorange="reversed",
            showgrid=False,
            zeroline=False,
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=TOKENS["rule"],
            zeroline=True,
            zerolinecolor=TOKENS["ink_4"],
            zerolinewidth=1,
        ),
        annotations=[
            dict(
                x=0.5,
                y=1.02,
                xref="paper",
                yref="paper",
                text=f"Fastest Lap: {pole_time_str} ({df.iloc[0]['Driver']})",
                showarrow=False,
                font=dict(family=TOKENS["font_display"], size=13, color=TOKENS["ink_2"]),
            )
        ],
    )

    st.markdown(
        '<div class="section-head">Qualifying<span class="hint">fastest lap deltas from pole position</span></div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, use_container_width=True, key="qualifying_chart")
