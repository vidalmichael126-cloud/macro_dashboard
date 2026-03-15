"""
app.py — Main Streamlit entry point.
Routes between the three dashboard views using tab navigation.
Run locally:  streamlit run app.py
Deploy:       Push to GitHub, connect to Streamlit Cloud (share.streamlit.io)
"""

import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Macro Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Minimal CSS — clean the default Streamlit chrome
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    div[data-testid="stTab"] button {font-size: 13px; font-weight: 500;}
</style>
""", unsafe_allow_html=True)

# ── Tab routing ───────────────────────────────────────────────────────────────
# Tabs are ordered: Morning Brief (default) → Signal Board → Regime Board
# Views can request tab switches via st.session_state["active_tab"]

from views.morning_brief import render as render_morning
from views.signal_board   import render as render_signals
from views.regime_board   import render as render_regime

tab_names  = ["📋 Morning brief", "📊 Signal board", "🎯 Regime board"]
tab_labels = ["Morning Brief",   "Signal Board",    "Regime Board"]

# Determine which tab to open (allows programmatic switching from view buttons)
default_idx = 0
if "active_tab" in st.session_state:
    target = st.session_state.get("active_tab", "Morning Brief")
    if target in tab_labels:
        default_idx = tab_labels.index(target)

tabs = st.tabs(tab_names)

with tabs[0]:
    render_morning()

with tabs[1]:
    render_signals()

with tabs[2]:
    render_regime()
