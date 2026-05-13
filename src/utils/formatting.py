"""Pure formatting helpers — no streamlit, no fastf1."""
import pandas as pd


def ordinal(n):
    try:
        n = int(n)
    except (ValueError, TypeError):
        return str(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_time_or_gap(is_winner, time, status):
    if is_winner and pd.notna(time):
        total = time.total_seconds() if isinstance(time, pd.Timedelta) else float(time)
        hours = int(total // 3600)
        mins = int((total % 3600) // 60)
        secs = total % 60
        if hours:
            return f"{hours}:{mins:02d}:{secs:06.3f}"
        return f"{mins}:{secs:06.3f}"
    if isinstance(status, str) and status.startswith("+"):
        return status
    if pd.notna(time):
        secs = time.total_seconds() if isinstance(time, pd.Timedelta) else float(time)
        return f"+{secs:.3f}s"
    return "—"
