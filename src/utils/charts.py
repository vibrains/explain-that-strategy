"""Plotly chart theming helpers."""
from src.config import TOKENS


def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# Translucent overlays for safety-car / VSC / rain windows on time-series charts.
OVERLAY = {
    "SC":   hex_to_rgba(TOKENS["alert"], 0.30),
    "VSC":  hex_to_rgba(TOKENS["warn"],  0.30),
    "rain": hex_to_rgba(TOKENS["info"],  0.25),
}


def apply_chart_theme(fig, height=400, x_title=None, y_title=None):
    """Normalize a plotly figure to the design system."""
    fig.update_layout(
        height=height,
        paper_bgcolor=TOKENS["paper_sh"],
        plot_bgcolor=TOKENS["paper_sh"],
        font=dict(family=TOKENS["font"], color=TOKENS["ink"], size=13),
        margin=dict(l=20, r=20, t=28, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TOKENS["ink_2"]),
        ),
        xaxis=dict(
            title=dict(text=x_title, font=dict(color=TOKENS["ink_2"])) if x_title else None,
            gridcolor=TOKENS["rule"],
            linecolor=TOKENS["ink_4"],
            tickcolor=TOKENS["ink_4"],
            tickfont=dict(color=TOKENS["ink_2"]),
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(color=TOKENS["ink_2"])) if y_title else None,
            gridcolor=TOKENS["rule"],
            linecolor=TOKENS["ink_4"],
            tickcolor=TOKENS["ink_4"],
            tickfont=dict(color=TOKENS["ink_2"]),
            zeroline=False,
        ),
    )
    return fig


def add_race_overlays(fig, sc_periods_mapped, weather_summary, layer="below", show_annotations=True):
    """Add SC/VSC/rain shaded regions to a figure with a lap-based x-axis."""
    if weather_summary and weather_summary.get("rain_windows"):
        for rstart, rend in weather_summary["rain_windows"]:
            fig.add_vrect(
                x0=rstart - 0.5,
                x1=rend + 0.5,
                fillcolor=OVERLAY["rain"],
                layer=layer,
                line_width=0,
                annotation_text="Rain" if show_annotations else None,
                annotation_position="top right",
                annotation=dict(
                    font_size=12, font_color="#FFFFFF", font_weight="bold",
                    bgcolor=TOKENS["info"], borderpad=3, opacity=0.9,
                ),
            )
    for period in sc_periods_mapped or []:
        color = OVERLAY["VSC"] if period["type"] == "VSC" else OVERLAY["SC"]
        fig.add_vrect(
            x0=period["start_lap"] - 0.5,
            x1=period["end_lap"] + 0.5,
            fillcolor=color,
            layer=layer,
            line_width=0,
            annotation_text=period["type"] if show_annotations else None,
            annotation_position="top left",
            annotation=dict(
                font_size=12, font_color="#FFFFFF", font_weight="bold",
                bgcolor=TOKENS["alert"] if period["type"] == "SC" else TOKENS["warn"],
                borderpad=3, opacity=0.9,
            ),
        )
