"""Narrative driver summary line: name, team, story, points."""
import pandas as pd
import streamlit as st

from src.config import TOKENS
from src.utils.formatting import ordinal


def render_driver_summary(row, driver_code):
    classified = row.get("ClassifiedPosition")
    position = row.get("Position")
    status = row.get("Status", "") or ""
    points = row.get("Points", 0)
    grid = row.get("GridPosition")
    team = row.get("TeamName", "")
    full_name = row.get("FullName", driver_code)
    headshot = row.get("HeadshotUrl") or ""
    team_color = (
        f"#{row['TeamColor']}"
        if pd.notna(row.get("TeamColor")) and row.get("TeamColor")
        else TOKENS["ink_4"]
    )

    pos_display = classified if pd.notna(classified) and str(classified).strip() else (
        f"{int(position)}" if pd.notna(position) else "—"
    )
    pos_label = ordinal(pos_display) if str(pos_display).isdigit() else str(pos_display)
    grid_label = ordinal(int(grid)) if pd.notna(grid) and int(grid) > 0 else "Pit Lane"
    dnf = status and status != "Finished" and not str(status).startswith("+")

    if dnf:
        story = f"Retired · {status}"
    elif pd.notna(grid) and str(pos_display).isdigit() and int(grid) > 0:
        gained = int(grid) - int(pos_display)
        if gained > 0:
            story = f"Finished {pos_label} from {grid_label} · +{gained} places"
        elif gained < 0:
            story = f"Finished {pos_label} from {grid_label} · {gained} places"
        else:
            story = f"Finished {pos_label} from {grid_label}"
    else:
        story = f"Finished {pos_label}"

    pts_text = f"{points:g} pts" if pd.notna(points) and points else "No points"

    photo_html = (
        f"<img src='{headshot}' alt='' loading='lazy' "
        f"style='width:52px;height:52px;border-radius:50%;object-fit:cover;"
        f"object-position:top;background:var(--paper-shade);flex-shrink:0;'>"
        if headshot else ""
    )

    st.markdown(
        f"<div id='driver-summary' style='margin-top:22px;padding:16px 0;"
        f"scroll-margin-top:140px;"
        f"border-top:1px solid var(--rule-soft);border-bottom:1px solid var(--rule-soft);"
        f"display:flex;align-items:center;gap:14px;'>"
        f"<div style='width:4px;height:44px;background:{team_color};'></div>"
        f"{photo_html}"
        f"<div style='flex:1;'>"
        f"<div style='font-size:var(--text-lg);font-weight:600;color:var(--ink);'>{full_name}</div>"
        f"<div style='color:var(--ink-3);font-size:var(--text-sm);margin-top:2px;'>"
        f"{team or '—'} · {story} · {pts_text}</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
