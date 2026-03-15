"""
views/regime_board.py — Dashboard A: The decision view.
Used when making an actual investment decision.
Shows scenario probabilities, full action rules, and combo analysis.
"""

import streamlit as st
from data_feeds import fetch_live_prices, get_current_value, format_price, format_pct
from signal_engine import get_full_analysis, STATUS_COLORS, SEVERITY_COLORS
from config import SCENARIOS, COMBINATION_RULES


def render():
    analysis = get_full_analysis()
    prices   = analysis["prices"]
    statuses = analysis["statuses"]
    rules    = analysis["rules"]
    probs    = analysis["probs"]
    scenario = analysis["scenario"]

    st.markdown("### Regime board — decision view")
    st.caption(
        "Use this view when making an actual position decision. "
        "Read top to bottom: scenario → signals → combination rules → actions."
    )

    # ── Scenario probability selector ─────────────────────────────────────────
    st.markdown("**Current scenario probabilities**")

    # Large 3-column scenario display
    sc_cols = st.columns(3)
    for i, (letter, sc) in enumerate(SCENARIOS.items()):
        prob       = probs[letter]
        is_dominant = (letter == scenario)
        border_width = "2px" if is_dominant else "0.5px"

        with sc_cols[i]:
            click_key = f"sc_select_{letter}"
            if st.button(
                f"{sc['name']}\n{prob}%\n{sc['oil_range']}",
                key=click_key,
                use_container_width=True,
            ):
                st.session_state["selected_scenario"] = letter

    selected = st.session_state.get("selected_scenario", scenario)
    sc_data  = SCENARIOS[selected]

    st.markdown(
        f"""<div style='background:{sc_data["color_bg"]};
        border:2px solid {sc_data["color_border"]};
        border-radius:12px;padding:16px 20px;margin:12px 0'>
          <div style='font-size:18px;font-weight:500;
          color:{sc_data["color_text"]}'>{sc_data["name"]}</div>
          <div style='font-size:13px;color:{sc_data["color_subtext"]};
          margin-top:4px'>{sc_data["description"]}</div>
          <div style='font-size:13px;color:{sc_data["color_subtext"]};
          margin-top:4px'>Oil: {sc_data["oil_range"]}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── What needs to be true for this scenario ───────────────────────────────
    st.markdown(f"**What confirms {selected == 'A' and 'Scenario A' or selected == 'B' and 'Scenario B' or 'Scenario C'}**")

    scenario_conditions = {
        "A": [
            ("WTI oil falls below $90",       "oil",      None),
            ("XLE begins diverging from oil",  "xle_divergence", None),
            ("VIX falls below 20 (calm)",      "vix",      None),
            ("KOSPI (EWY) recovers strongly",  None,       None),
        ],
        "B": [
            ("WTI oil holds $100–150",         "oil",      None),
            ("VIX stays 25–35 (stress)",       "vix",      None),
            ("10yr yield grinds higher",       "yield_10", None),
            ("KOSPI stabilizes but weak",      None,       None),
        ],
        "C": [
            ("WTI oil exceeds $150",           "oil",      None),
            ("VIX spikes above 40",            "vix",      None),
            ("Japan/Korea sell Treasuries heavily", None,  None),
            ("USD/JPY breaks 155 (carry unwind)", "usdjpy", None),
        ],
    }

    for condition_text, sig_key, _ in scenario_conditions.get(selected, []):
        if sig_key:
            sig    = statuses.get(sig_key, {})
            status = sig.get("status", "normal")
            col    = STATUS_COLORS.get(status)

            # Check if condition is met for this scenario
            confirmed = _condition_confirmed(sig_key, status, selected)
            icon  = "✓" if confirmed else "○"
            color = col["text"] if confirmed else "gray"
        else:
            icon, color = "○", "gray"

        st.markdown(
            f"<div style='padding:7px 0;border-bottom:.5px solid rgba(128,128,128,.12);"
            f"font-size:13px;color:{color}'>{icon} {condition_text}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Signal status table ───────────────────────────────────────────────────
    st.markdown("**Signal status at a glance**")

    signal_display = [
        ("oil",           "WTI crude oil"),
        ("vix",           "VIX"),
        ("yield_10",      "10yr yield"),
        ("usdjpy",        "USD/JPY"),
        ("yield_curve",   "Yield curve (2s10s)"),
        ("xle_divergence","XLE/oil divergence"),
    ]

    for key, label in signal_display:
        sig    = statuses.get(key, {})
        val    = sig.get("value")
        status = sig.get("status", "normal")
        col    = STATUS_COLORS.get(status)
        val_str = f"{val:.2f}" if val is not None else "—"
        unit   = sig.get("unit", "")

        st.markdown(
            f"""<div style='display:flex;align-items:center;gap:10px;
            padding:7px 12px;background:{col["bg"]};
            border-radius:6px;margin-bottom:4px'>
              <div style='width:8px;height:8px;border-radius:50%;
              background:{col["border"]};flex-shrink:0'></div>
              <div style='flex:1;font-size:13px;color:{col["text"]}'>{label}</div>
              <div style='font-size:13px;font-weight:500;color:{col["text"]}'>
                {val_str}{unit}</div>
              <div style='font-size:11px;color:{col["text"]};
              background:rgba(255,255,255,.4);padding:2px 7px;
              border-radius:4px'>{col["label"]}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Active combination rules ───────────────────────────────────────────────
    st.markdown("**Combination rules status**")

    active_rules = [r for r in rules if r.get("state") == "active"]
    watch_rules  = [r for r in rules if r.get("state") == "watch"]
    silent_rules = [
        r for r in COMBINATION_RULES
        if r["name"] not in [x["name"] for x in active_rules + watch_rules]
    ]

    for rule in active_rules:
        sev = rule.get("severity", "warning")
        col = SEVERITY_COLORS.get(sev, STATUS_COLORS["warning"])
        st.markdown(
            f"""<div style='background:{col["bg"]};border:1.5px solid {col["border"]};
            border-radius:8px;padding:12px 16px;margin-bottom:8px'>
              <div style='display:flex;justify-content:space-between'>
                <span style='font-weight:500;color:{col["text"]};font-size:14px'>{rule["name"]}</span>
                <span style='background:{col["border"]};color:white;font-size:11px;
                padding:2px 8px;border-radius:4px;font-weight:500'>ACTIVE</span>
              </div>
              <div style='font-size:12px;color:{col["text"]};opacity:.85;
              margin-top:5px'>{rule["description"]}</div>
              <div style='font-size:12px;color:{col["text"]};margin-top:8px;
              padding-top:8px;border-top:.5px solid rgba(255,255,255,.3)'>
              <strong>Action now:</strong> {rule.get("action","")}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    for rule in watch_rules:
        col     = STATUS_COLORS["elevated"]
        missing = ", ".join(rule.get("missing", []))
        st.markdown(
            f"""<div style='background:{col["bg"]};border:.5px solid {col["border"]};
            border-radius:8px;padding:10px 14px;margin-bottom:6px'>
              <div style='display:flex;justify-content:space-between'>
                <span style='font-weight:500;color:{col["text"]};font-size:13px'>{rule["name"]}</span>
                <span style='font-size:11px;color:{col["text"]};opacity:.7'>WATCH</span>
              </div>
              <div style='font-size:12px;color:{col["text"]};opacity:.8;margin-top:3px'>
                Missing: {missing or "near threshold"}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    if not active_rules and not watch_rules:
        st.info("No combination rules active. All signals within normal ranges.")

    for rule in silent_rules[:3]:
        col = STATUS_COLORS["normal"]
        st.markdown(
            f"""<div style='background:{col["bg"]};border:.5px solid {col["border"]};
            border-radius:8px;padding:8px 14px;margin-bottom:4px;opacity:.6'>
              <div style='font-size:12px;font-weight:500;color:{col["text"]}'>{rule["name"]} — not active</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Action checklist ───────────────────────────────────────────────────────
    st.markdown(f"**Action checklist for {sc_data['name']}**")
    st.caption(
        "These are the rules for the *current dominant scenario*. "
        "Check them before executing any trade."
    )

    for i, action in enumerate(sc_data["actions"]):
        checked = st.checkbox(action, key=f"action_{selected}_{i}")

    st.divider()

    # ── Scenario probability context ───────────────────────────────────────────
    st.markdown("**Why these probabilities?**")

    oil_val    = statuses.get("oil",    {}).get("value")
    vix_val    = statuses.get("vix",    {}).get("value")
    xle_div    = statuses.get("xle_divergence", {}).get("diverging", False)
    usdjpy_val = statuses.get("usdjpy", {}).get("value")

    factors = []
    if oil_val and oil_val > 150:
        factors.append("Oil above $150 strongly weights toward Scenario C (+30% C)")
    elif oil_val and oil_val > 120:
        factors.append("Oil above $120 weighs toward B, away from A")
    elif oil_val and oil_val < 90:
        factors.append("Oil below $90 strongly weights toward Scenario A (+20% A)")
    if xle_div:
        factors.append("XLE diverging from oil — early peace signal (+15% A, −10% B)")
    if vix_val and vix_val > 40:
        factors.append("VIX above 40 — capitulation, often marks turn (+5% A)")
    if usdjpy_val and usdjpy_val > 155:
        factors.append("USD/JPY critical — systemic risk rising (+5% C)")

    if factors:
        for f in factors:
            st.markdown(f"- {f}")
    else:
        st.caption("Using default probabilities — no strong signal adjustments.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("← Signal board"):
            st.session_state["active_tab"] = "Signal Board"
            st.rerun()
    with col_b2:
        if st.button("← Morning brief"):
            st.session_state["active_tab"] = "Morning Brief"
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _condition_confirmed(sig_key, status, scenario):
    """Check whether a given signal's current status confirms a scenario."""
    confirmation_map = {
        "A": {"oil": ["normal"], "vix": ["normal"], "xle_divergence": ["warning", "critical"]},
        "B": {"oil": ["elevated", "warning"], "vix": ["elevated", "warning"],
              "yield_10": ["elevated", "warning", "critical"]},
        "C": {"oil": ["critical"], "vix": ["critical"], "usdjpy": ["critical"]},
    }
    confirmed_statuses = confirmation_map.get(scenario, {}).get(sig_key, [])
    return status in confirmed_statuses
