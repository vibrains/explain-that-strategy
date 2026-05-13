"""Final summary verdict comparing the optimal simulated strategy to reality."""
import pandas as pd
import streamlit as st

from src.config import PIT_STOP_LOSS_NORMAL, VERDICT_SIGNIFICANT_THRESHOLD


def render_verdict(results_df: pd.DataFrame) -> None:
    if results_df.empty:
        return

    best = results_df.iloc[0]
    st.markdown('<div class="section-head">Verdict</div>', unsafe_allow_html=True)

    if best["Delta"] < VERDICT_SIGNIFICANT_THRESHOLD:
        sc_msg = ""
        if best.get("SC Opportunistic"):
            sc_msg = (
                " This was an SC-opportunistic strategy — pitting during a safety car "
                "period for a cheap stop."
            )
        st.markdown(
            f'<div class="verdict-card">'
            f"The optimal simulated strategy was <b>{best['Strategy']}</b>, "
            f"which could have saved <b>{abs(best['Delta']):.1f}s</b>.{sc_msg} "
            f"Roughly <b>{abs(best['Delta'])/PIT_STOP_LOSS_NORMAL:.1f}</b> pit stops worth of time.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="verdict-card verdict-card--nailed">'
            "The team nailed it — no significantly faster strategy found in simulation.</div>",
            unsafe_allow_html=True,
        )
