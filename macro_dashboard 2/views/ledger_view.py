"""
views/ledger_view.py — Weekly prediction ledger UI.
Tab: "Weekly ledger"

Two modes:
  1. Entry mode (Mon–Thu): file hypotheses for the week
  2. Review mode (Fri–Sat): score outcomes, file notes, export
"""

import streamlit as st
from datetime import date, datetime
from prediction_ledger import (
    get_or_create_week, get_all_weeks, get_current_week_key,
    get_week_label, get_rolling_accuracy, get_accuracy_status,
    get_model_vs_manual_split,
    add_hypothesis, delete_hypothesis, score_hypothesis,
    update_week_notes, export_ledger_json,
)
from config import LEDGER_SCORING


# ─── Color helpers ────────────────────────────────────────────────────────────

def _score_color(score):
    if score is None:  return "gray"
    if score == 2:     return "#27500A"
    if score == 1:     return "#185FA5"
    if score == 0:     return "#633806"
    return "#791F1F"

def _score_badge(score):
    if score is None:  return "⬜ pending"
    if score == 2:     return "✓ hit"
    if score == 1:     return "~ direction"
    if score == 0:     return "✗ miss"
    return "✗✗ confident miss"

def _acc_color(pct):
    if pct is None: return "gray"
    status = get_accuracy_status(pct)
    return {"excellent":"#27500A","good":"#185FA5","review":"#633806","rebuild":"#791F1F"}.get(status,"gray")

SIGNAL_OPTIONS = [
    "200-day MA break","VIX rising","Oil above $90","10yr yield",
    "HYG credit stress","PE basket lag","Gold 1979 tracker",
    "Japan JGB (JP10Y)","Episode tracker","Sell America rule",
    "Stagflation rule","Recession pricing","Geo intensity score",
    "Overnight transmission","XLE/oil divergence",
]

CONF_LABELS = {
    0: "Not set",
    1: "Low — weak signal basis",
    2: "Some — one signal confirming",
    3: "Moderate — clear thesis",
    4: "High — two streams confirming",
    5: "Very high — act on this",
}


# ─── Main render ─────────────────────────────────────────────────────────────

def render():
    now         = datetime.now()
    is_friday   = now.weekday() == 4
    is_saturday = now.weekday() == 5
    review_mode = is_friday or is_saturday

    week_key    = get_current_week_key()
    current     = get_or_create_week(week_key)
    all_weeks   = get_all_weeks()
    past_weeks  = [w for w in all_weeks if w["week_key"] != week_key]

    # ── Header ────────────────────────────────────────────────────────────────
    col_h, col_mode = st.columns([3, 1])
    with col_h:
        st.markdown(f"### Weekly ledger · {current['week_label']}")
    with col_mode:
        mode_label = "📋 Review mode" if review_mode else "📝 Entry mode"
        st.markdown(
            f"<div style='text-align:right;font-size:12px;color:gray;padding-top:8px'>"
            f"{mode_label}</div>", unsafe_allow_html=True
        )

    st.divider()

    # ── Accuracy summary ──────────────────────────────────────────────────────
    rolling  = get_rolling_accuracy(4)
    split    = get_model_vs_manual_split()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        acc = current.get("accuracy_pct")
        st.metric("This week", f"{acc:.0f}%" if acc is not None else "—",
                  help="Score 0–100% based on hypothesis outcomes")
    with col2:
        st.metric("4-week rolling", f"{rolling:.0f}%" if rolling is not None else "—",
                  delta="above 60% = model working" if rolling and rolling >= 60 else "below 60% = audit signals")
    with col3:
        ma = split["model_accuracy"]
        st.metric("Model accuracy", f"{ma:.0f}%" if ma is not None else "—",
                  help="When model signal predicted the outcome")
    with col4:
        st.metric("Audit threshold", "60%",
                  delta="Simons rule: 3 weeks below = rebuild", delta_color="off")

    st.divider()

    # ── Current week hypotheses ───────────────────────────────────────────────
    hyps = current.get("hypotheses", [])
    st.markdown(f"**This week's hypotheses** ({len(hyps)} filed)")

    if not hyps:
        st.caption("No hypotheses filed yet. Add one below.")
    else:
        for hyp in hyps:
            with st.container():
                col_h, col_s, col_d = st.columns([5, 1.2, 0.8])
                with col_h:
                    score = hyp.get("score")
                    color = _score_color(score)
                    st.markdown(
                        f"<div style='font-size:13px;font-weight:500;color:{color}'>"
                        f"{hyp['statement']}</div>",
                        unsafe_allow_html=True,
                    )
                    meta = []
                    if hyp.get("target"):    meta.append(f"Target: {hyp['target']}")
                    if hyp.get("direction"): meta.append(f"Direction: {hyp['direction']}")
                    if hyp.get("signals"):   meta.append(f"Signals: {', '.join(hyp['signals'])}")
                    if hyp.get("confidence"):
                        dots = "●" * hyp["confidence"] + "○" * (5 - hyp["confidence"])
                        meta.append(f"Confidence: {dots}")
                    st.caption(" · ".join(meta))

                with col_s:
                    badge = _score_badge(score)
                    st.markdown(
                        f"<div style='text-align:center;font-size:11px;font-weight:500;"
                        f"color:{color};padding-top:8px'>{badge}</div>",
                        unsafe_allow_html=True,
                    )

                with col_d:
                    if score is None:
                        if st.button("✕", key=f"del_{hyp['id']}", help="Remove hypothesis"):
                            delete_hypothesis(hyp["id"])
                            st.rerun()

                # Review mode: score outcomes inline
                if review_mode and hyp.get("score") is None:
                    with st.expander(f"File outcome for: {hyp['statement'][:60]}..."):
                        _render_score_form(hyp, week_key)

                # Show filed outcome
                if hyp.get("outcome"):
                    st.markdown(
                        f"<div style='font-size:11px;color:gray;margin:-4px 0 6px 0;"
                        f"padding:6px 10px;background:#f7f7f6;border-radius:5px'>"
                        f"<strong>Outcome:</strong> {hyp['outcome']}</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("<hr style='margin:6px 0;opacity:.15'>", unsafe_allow_html=True)

    # ── Add hypothesis form ───────────────────────────────────────────────────
    st.markdown("**File a new hypothesis**")

    with st.form("new_hyp_form", clear_on_submit=True):
        statement = st.text_input(
            "Prediction — specific and falsifiable",
            placeholder='e.g. "S&P closes below 6,300 by Friday"',
        )
        col_t, col_d = st.columns(2)
        with col_t:
            target = st.text_input("Target value", placeholder='e.g. "below 6,300"')
        with col_d:
            direction = st.selectbox(
                "Direction",
                ["", "above", "below", "up", "down", "fires", "holds"],
                format_func=lambda x: {
                    "":"Select direction","above":"Above threshold",
                    "below":"Below threshold","up":"Up from current",
                    "down":"Down from current","fires":"A rule fires","holds":"A level holds",
                }.get(x, x),
            )

        signals = st.multiselect(
            "Signal basis — which signals drove this prediction",
            options=SIGNAL_OPTIONS,
        )

        confidence = st.select_slider(
            "Confidence",
            options=[0, 1, 2, 3, 4, 5],
            value=0,
            format_func=lambda x: CONF_LABELS.get(x, str(x)),
        )

        submitted = st.form_submit_button("Add hypothesis →", use_container_width=True)
        if submitted:
            if not statement.strip():
                st.error("Please enter a prediction statement.")
            else:
                ok = add_hypothesis(
                    statement=statement,
                    target=target,
                    direction=direction,
                    signals=signals,
                    confidence=confidence,
                )
                if ok:
                    st.success("Hypothesis filed.")
                    st.rerun()

    st.divider()

    # ── Weekly notes ──────────────────────────────────────────────────────────
    if review_mode:
        st.markdown("**Weekly review notes**")
        notes = st.text_area(
            "What did we miss? What surprised us? Model lessons?",
            value=current.get("notes", ""),
            height=100,
            label_visibility="collapsed",
        )
        if st.button("Save notes"):
            update_week_notes(notes)
            st.success("Saved.")

    # ── Export ────────────────────────────────────────────────────────────────
    col_ex, _ = st.columns([1, 2])
    with col_ex:
        json_str = export_ledger_json()
        st.download_button(
            label="Export full ledger (JSON)",
            data=json_str,
            file_name=f"macro_ledger_{date.today().isoformat()}.json",
            mime="application/json",
            help="Download complete ledger history as backup",
        )

    st.divider()

    # ── Past weeks ────────────────────────────────────────────────────────────
    if past_weeks:
        st.markdown("**Past weeks**")
        for week in past_weeks[:8]:   # show last 8
            acc = week.get("accuracy_pct")
            acc_str = f"{acc:.0f}%" if acc is not None else "pending"
            color   = _acc_color(acc)

            with st.expander(
                f"{week['week_label']}  ·  {len(week['hypotheses'])} hypotheses  ·  {acc_str}",
                expanded=False,
            ):
                hyps_w = week.get("hypotheses", [])
                if not hyps_w:
                    st.caption("No hypotheses filed.")
                    continue

                for hyp in hyps_w:
                    score = hyp.get("score")
                    badge = _score_badge(score)
                    c     = _score_color(score)
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:baseline;padding:5px 0;border-bottom:0.5px solid #eee'>"
                        f"<span style='font-size:12px'>{hyp['statement']}</span>"
                        f"<span style='font-size:11px;font-weight:500;color:{c};margin-left:10px;flex-shrink:0'>{badge}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if hyp.get("outcome"):
                        st.caption(f"→ {hyp['outcome']}")

                if week.get("notes"):
                    st.markdown(
                        f"<div style='margin-top:8px;font-size:11px;color:gray;"
                        f"background:#f7f7f6;padding:8px 10px;border-radius:5px'>"
                        f"<strong>Notes:</strong> {week['notes']}</div>",
                        unsafe_allow_html=True,
                    )


# ─── Score form (review mode) ─────────────────────────────────────────────────

def _render_score_form(hyp: dict, week_key: str):
    outcome = st.text_area(
        "What actually happened?",
        placeholder="Plain English — what did the market do relative to this prediction?",
        key=f"out_{hyp['id']}",
    )
    col_sc, col_mp = st.columns(2)
    with col_sc:
        score = st.radio(
            "Score",
            options=[2, 1, 0, -1],
            format_func=lambda x: LEDGER_SCORING.get(x, str(x)),
            horizontal=False,
            key=f"sc_{hyp['id']}",
        )
    with col_mp:
        model_predicted = st.checkbox(
            "Model signal predicted this",
            key=f"mp_{hyp['id']}",
            help="Was there a signal in the dashboard that, if you'd followed it, would have called this correctly?",
        )
        missed_signal = st.text_input(
            "Missed signal (if any)",
            placeholder="Which signal would have caught this?",
            key=f"ms_{hyp['id']}",
        )

    if st.button("File outcome", key=f"file_{hyp['id']}"):
        if not outcome.strip():
            st.error("Please describe what happened.")
        else:
            score_hypothesis(
                hyp_id=hyp["id"],
                outcome_text=outcome,
                score=score,
                model_predicted=model_predicted,
                missed_signal=missed_signal,
                week_key=week_key,
            )
            st.success("Outcome filed.")
            st.rerun()
