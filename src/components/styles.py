"""Inject global CSS from assets/styles.css into the Streamlit app."""
from pathlib import Path

import streamlit as st

STYLES_PATH = Path(__file__).resolve().parents[2] / "assets" / "styles.css"


def inject_styles():
    css = STYLES_PATH.read_text(encoding="utf-8") if STYLES_PATH.exists() else ""
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
