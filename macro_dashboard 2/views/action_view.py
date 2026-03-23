"""
views/action_view.py — Burry-style action plan tab.
"""

import streamlit as st
from signal_engine import get_full_analysis
from config import ACTION_TRIGGERS

STATUS_META = {
    "enter":      {"bg":"#FAEEDA","border":"#EF9F27","text":"#412402","label":"Enter now"},
    "watch":      {"bg":"#FAEEDA","border":"#EF9F27","text":"#633806","label":"Watch"},
    "active":     {"bg":"#EAF3DE","border":"#639922","text":"#27500A","label":"Active — hold"},
    "monitoring": {"bg":"#F1EFE8","border":"#B4B2A9","text":"#5F5E5A","label":"Monitoring"},
    "exit":       {"bg":"#FCEBEB","border":"#E24B4A","text":"#791F1F","label":"Exit signal"},
}


def _badge(status):
    m = STATUS_META.get(status, STATUS_META["monitoring"])
    return (
        f"<span style='padding:3px 9px;border-radius:4px;font-size:11px;"
        f"font-weight:600;background:{m['bg']};color:{m['text']};"
        f"border:1px solid {m['border']}'>{m['label']}</span>"
    )


def render():
    analysis = get_full_analysis()
    triggers = analysis.get("action_triggers", ACTION_TRIGGERS)

    st.markdown("### Action plan · Burry engine")
    st.caption("Trigger status recalculates each load. Enter only when model conditions are met.")
    st.divider()

    for t in triggers:
        status = t.get("status", "monitoring")
        m      = STATUS_META.get(status, STATUS_META["monitoring"])
        met    = t.get("conditions_met", [])
        bw     = "1.5px" if status in ["enter","exit"] else "0.5px"

        header_html = (
            f"<div style='border:{bw} solid {m['border']};border-radius:10px;"
            f"padding:12px 16px;margin-bottom:4px;background:{m['bg']}'>"
            f"<div style='display:flex;justify-content:space-between;align-items:start;margin-bottom:6px'>"
            f"<div><div style='font-size:13px;font-weight:500;color:{m['text']}'>{t['name']}</div>"
            f"<div style='font-size:10px;font-family:monospace;color:{m['text']};opacity:.65;margin-top:1px'>"
            f"{t.get('account','').upper()}</div></div>"
            f"{_badge(status)}</div>"
            f"<div style='font-size:11px;color:{m['text']};opacity:.85;line-height:1.6'>"
            f"{t.get('thesis','')[:220]}...</div></div>"
        )
        st.markdown(header_html, unsafe_allow_html=True)

        with st.expander(f"Details — {t['name']}", expanded=(status == "enter")):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Entry conditions**")
                for cond in t.get("entry_conditions", []):
                    # simple check: condition text appears in met list
                    is_met = any(m_item in cond or cond in m_item for m_item in met)
                    icon   = "✓" if is_met else "✗"
                    color  = "#27500A" if is_met else "#888"
                    st.markdown(
                        f"<div style='font-size:11px;color:{color};padding:2px 0'>"
                        f"{icon}&nbsp;&nbsp;{cond}</div>",
                        unsafe_allow_html=True,
                    )
                st.caption(f"Logic: {t.get('entry_logic','AND')}")

            with c2:
                st.markdown("**Position details**")
                rows = [
                    ("Instrument", t.get("instrument","")),
                    ("Strike",     t.get("strike","")),
                    ("Expiry",     t.get("expiry","")),
                    ("Account",    t.get("account","")),
                    ("Size",       t.get("size","")),
                ]
                for lbl, val in rows:
                    if val:
                        st.markdown(
                            f"<div style='display:flex;justify-content:space-between;"
                            f"font-size:11px;padding:3px 0;"
                            f"border-bottom:0.5px solid rgba(0,0,0,.06)'>"
                            f"<span style='color:gray'>{lbl}</span>"
                            f"<span>{val}</span></div>",
                            unsafe_allow_html=True,
                        )

            exit_html = (
                "<div style='margin-top:8px;padding:7px 10px;"
                "background:#FCEBEB;border:0.5px solid #F09595;"
                "border-radius:6px;font-size:11px;color:#791F1F;line-height:1.5'>"
                f"<strong>Exit / invalidation:</strong> {t.get('exit_stop','')}</div>"
            )
            st.markdown(exit_html, unsafe_allow_html=True)

    st.divider()
    st.markdown("**Iron rules**")
    for rule in [
        "Total put premium never exceeds 5% of investable assets.",
        "All puts go in the Roth IRA — 40.8% tax in taxable destroys the asymmetry.",
        "Two independent signals must confirm before any entry. One stream = noise.",
        "Exit on thesis change, not price movement.",
        "Cash preservation through June 2026 — no new positions until Banner paycheck confirmed.",
    ]:
        st.markdown(f"— {rule}")
