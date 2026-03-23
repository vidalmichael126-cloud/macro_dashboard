"""views/scenario_view.py — Scenario model tab."""
import streamlit as st
from signal_engine import get_full_analysis
from config import SCENARIOS, HISTORICAL_EPISODES, STRUCTURAL_PRIORS


def render():
    analysis  = get_full_analysis()
    probs     = analysis["probs"]
    scenario  = analysis["scenario"]
    drivers   = analysis.get("prob_drivers", [])
    episode   = analysis.get("episode", {})

    st.markdown("### Scenario model")
    st.caption("Base rates start with Dalio structural priors baked in. Signal conditions add or subtract. Renormalized to 100%.")
    st.divider()

    # ── Probability bars ──────────────────────────────────────────────────────
    sc_colors = {"A":"#639922","B":"#d4a847","C":"#E24B4A"}
    for key in ["A","B","C"]:
        sc   = SCENARIOS[key]
        pct  = probs[key]
        col  = sc_colors[key]
        is_current = key == scenario

        label = sc["name"] + (" ★" if is_current else "")
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;padding:8px 0;"
            f"border-bottom:0.5px solid rgba(0,0,0,.07)'>"
            f"<div style='font-size:12px;font-weight:{'600' if is_current else '400'};"
            f"width:180px;flex-shrink:0;color:{col}'>{label}</div>"
            f"<div style='flex:1;height:6px;background:#eee;border-radius:3px;overflow:hidden'>"
            f"<div style='width:{pct}%;height:100%;background:{col};border-radius:3px'></div></div>"
            f"<div style='font-size:14px;font-weight:500;width:38px;text-align:right;color:{col}'>{pct}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Probability drivers ───────────────────────────────────────────────────
    st.markdown("**Why these probabilities — every scoring rule shown**")
    for d in drivers:
        fired = d.get("fired", False)
        ia, ib, ic = d.get("impact_a",0), d.get("impact_b",0), d.get("impact_c",0)
        opacity = "1.0" if fired else "0.4"
        icon    = "✓" if fired else "○"
        color   = "#0f0f0f" if fired else "#aaa"

        c_str = f"A:{ia:+d} · B:{ib:+d} · C:{ic:+d}"
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:baseline;font-size:11px;padding:4px 0;"
            f"border-bottom:0.5px solid rgba(0,0,0,.05);opacity:{opacity}'>"
            f"<span style='color:{color}'>{icon}  {d.get('note','')}</span>"
            f"<span style='font-family:monospace;color:gray;font-size:10px'>{c_str}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Historical episode tracker ────────────────────────────────────────────
    st.markdown("**Historical analog tracker**")
    if not episode.get("ok"):
        st.caption("Insufficient data — check again after day 30.")
    else:
        best  = episode.get("best_match","—")
        conf  = episode.get("confidence", 0)
        note  = episode.get("note","")
        scores = episode.get("scores",{})

        st.info(note)
        cols = st.columns(len(scores))
        for col, (ep_id, score) in zip(cols, sorted(scores.items(), key=lambda x:-x[1])):
            ep_data = HISTORICAL_EPISODES.get(ep_id,{})
            is_best = ep_id == best
            with col:
                st.metric(
                    ep_data.get("label", ep_id),
                    f"{score:.0%}",
                    delta="best match" if is_best else None,
                )

    st.divider()

    # ── Structural prior callout ──────────────────────────────────────────────
    st.markdown("**Dalio structural prior — permanently baked into base rates**")
    sp = STRUCTURAL_PRIORS
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Debt / GDP", f"{sp['debt_gdp_pct']}%",
                  delta=f"Scenario C bias: {sp['scenario_c_bias']:+d}pts",
                  help="At 102%, the Fed cannot execute a Volcker-style rate shock without triggering a debt crisis.")
    with col2:
        st.metric("Petrodollar strain", "Active" if sp["petrodollar_strain"] else "Stable",
                  delta="Reserve currency risk elevated")
    with col3:
        st.metric("Fed room to hike", "No" if not sp["fed_room_to_hike"] else "Yes",
                  delta="Fiscal dominance constraint",
                  delta_color="inverse")
