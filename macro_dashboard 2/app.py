"""
app.py — Macro Signal Ledger · Burry Engine v1
Seven tabs: Signals · Rules · Scenario · Action plan · Weekly ledger · Burry playbook · Dalio overlay
"""

import streamlit as st
from config import APP_TITLE, APP_ICON, APP_SUBTITLE

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global style tweaks ───────────────────────────────────────────────────────
st.markdown("""
<style>
  div[data-testid="stTab"] button {font-size:12px;font-weight:500}
  .block-container {padding-top:1.5rem;max-width:1100px}
  div[data-testid="metric-container"] {background:var(--secondary-background-color);
    border-radius:8px;padding:.6rem .8rem}
</style>
""", unsafe_allow_html=True)

# ── App header ────────────────────────────────────────────────────────────────
col_title, col_meta = st.columns([3, 1])
with col_title:
    st.markdown(f"## {APP_ICON} {APP_TITLE}")
    st.caption(APP_SUBTITLE)
with col_meta:
    from datetime import datetime
    st.markdown(
        f"<div style='text-align:right;font-size:12px;color:gray;padding-top:12px'>"
        f"Live · {datetime.now().strftime('%a %b %d %Y · %I:%M %p')}</div>",
        unsafe_allow_html=True,
    )

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📡 Signals",
    "⚡ Rules",
    "🎯 Scenario",
    "🎬 Action plan",
    "📓 Weekly ledger",
    "📘 Burry playbook",
    "🌐 Dalio overlay",
])

with tabs[0]:
    from views.signal_ledger_view import render as render_signals
    render_signals()

with tabs[1]:
    from views.rules_view import render as render_rules
    render_rules()

with tabs[2]:
    from views.scenario_view import render as render_scenario
    render_scenario()

with tabs[3]:
    from views.action_view import render as render_actions
    render_actions()

with tabs[4]:
    from views.ledger_view import render as render_ledger
    render_ledger()

with tabs[5]:
    from views.burry_view import render as render_burry
    render_burry()

with tabs[6]:
    from views.dalio_view import render as render_dalio
    render_dalio()
