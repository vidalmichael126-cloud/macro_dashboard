"""
views/signal_board.py — Dashboard B: Full signal grid with sparklines.
Shows what changed, velocity, distance from thresholds.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
from data_feeds import (
    fetch_live_prices, fetch_sparklines, fetch_all_fred,
    get_current_value, format_price, format_pct, format_change
)
from signal_engine import (
    get_full_analysis, status_color, STATUS_COLORS
)
from config import THRESHOLDS, SCENARIOS, SPARKLINE_DAYS


def render():
    analysis = get_full_analysis()
    prices   = analysis["prices"]
    statuses = analysis["statuses"]
    rules    = analysis["rules"]
    probs    = analysis["probs"]
    sparks   = fetch_sparklines()

    st.markdown("### Signal board — full detail")
    st.caption(
        f"All tracked signals with {SPARKLINE_DAYS}-day sparklines · "
        "Status bars show distance to threshold"
    )

    # ── Filter bar ─────────────────────────────────────────────────────────────
    col_f1, col_f2, _, col_refresh = st.columns([1, 1, 3, 1])
    with col_f1:
        show_only_active = st.checkbox("Active only", value=False)
    with col_f2:
        show_all_tickers = st.checkbox("Show all tickers", value=False)
    with col_refresh:
        if st.button("Refresh ↺"):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # ── Primary signals ────────────────────────────────────────────────────────
    st.markdown("**Primary signals**")

    primary = [
        ("oil",      "WTI crude oil",    "oil",      "$",   2,  False),
        ("vix",      "VIX (fear index)", "vix",      "",    1,  False),
        ("yield_10", "10yr Treasury",    "yield_10", "",    2,  True),
        ("usdjpy",   "USD / JPY",        "usdjpy",   "",    1,  False),
    ]

    _render_signal_grid(primary, statuses, prices, sparks,
                        show_only_active=show_only_active)

    # ── Market signals ─────────────────────────────────────────────────────────
    st.markdown("**Market signals**")

    market = [
        ("gold",  "Gold (GLD)",     "gold",  "$", 2, False),
        ("xle",   "Energy (XLE)",   "xle",   "$", 2, False),
        ("hyg",   "Junk bonds HYG", "hyg",   "$", 2, False),
        ("sp500", "S&P 500",        "sp500", "",  0, False),
    ]
    _render_signal_grid(market, statuses, prices, sparks,
                        show_only_active=show_only_active)

    # ── Asian market signals ───────────────────────────────────────────────────
    st.markdown("**Asian market signals**")

    asian = [
        ("ewy", "South Korea (EWY)", "ewy", "$", 2, False),
        ("ewj", "Japan (EWJ)",       "ewj", "$", 2, False),
    ]
    _render_signal_grid(asian, statuses, prices, sparks,
                        show_only_active=show_only_active)

    # ── XLE / Oil divergence special card ─────────────────────────────────────
    div_status = statuses.get("xle_divergence", {})
    div_col    = status_color(div_status.get("status", "normal"))
    st.markdown("**XLE / oil divergence signal**")
    st.markdown(
        f"""<div style='background:{div_col["bg"]};border:.5px solid {div_col["border"]};
        border-radius:10px;padding:14px 16px;margin-bottom:12px'>
          <div style='display:flex;justify-content:space-between;align-items:center'>
            <div>
              <div style='font-weight:500;color:{div_col["text"]};font-size:14px'>
                XLE vs oil divergence</div>
              <div style='font-size:12px;color:{div_col["text"]};opacity:.8;margin-top:4px'>
                {div_status.get("note", "—")}</div>
            </div>
            <div style='font-size:20px;font-weight:500;color:{div_col["text"]}'>
              {"FIRING" if div_status.get("diverging") else "No signal"}
            </div>
          </div>
          <div style='font-size:11px;color:{div_col["text"]};opacity:.7;margin-top:8px'>
            Signal fires when XLE falls &gt;1% while oil is still above $90. 
            Historically precedes oil peak by 3–6 weeks.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Combination rules ──────────────────────────────────────────────────────
    st.markdown("**Signal combinations**")

    active_rules  = [r for r in rules if r.get("state") == "active"]
    watch_rules   = [r for r in rules if r.get("state") == "watch"]

    if not active_rules and not watch_rules:
        st.info("No combination rules active or near-active right now.")
    else:
        for rule in active_rules + watch_rules:
            state  = rule.get("state", "watch")
            sev    = rule.get("severity", "warning")
            if state == "active":
                col = STATUS_COLORS.get("critical" if sev == "critical" else "warning")
                badge = "ACTIVE"
            else:
                col   = STATUS_COLORS["elevated"]
                badge = "WATCH"

            met_str = ", ".join(rule.get("conditions_met", []))
            missing = rule.get("missing", [])

            st.markdown(
                f"""<div style='background:{col["bg"]};border:.5px solid {col["border"]};
                border-radius:8px;padding:12px 16px;margin-bottom:8px'>
                  <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                    <div style='font-weight:500;color:{col["text"]};font-size:14px'>{rule["name"]}</div>
                    <span style='background:{col["border"]};color:white;font-size:11px;
                    padding:2px 8px;border-radius:4px;font-weight:500'>{badge}</span>
                  </div>
                  <div style='font-size:12px;color:{col["text"]};opacity:.85;margin-top:4px'>
                    {rule["description"]}</div>
                  {'<div style="font-size:12px;color:' + col["text"] + ';margin-top:6px">'
                   '<strong>Action:</strong> ' + rule.get("action","") + '</div>' if state == "active" else ""}
                  {'<div style="font-size:11px;color:' + col["text"] + ';opacity:.7;margin-top:4px">'
                   'Conditions met: ' + (met_str or "none") + 
                   (' · Missing: ' + ', '.join(missing) if missing else '') + '</div>' if met_str else ""}
                </div>""",
                unsafe_allow_html=True,
            )

    # ── Scenario probability summary ───────────────────────────────────────────
    st.divider()
    st.markdown("**Scenario probabilities (model-scored)**")

    sc_cols = st.columns(3)
    for i, (letter, sc) in enumerate(SCENARIOS.items()):
        prob = probs[letter]
        with sc_cols[i]:
            is_dominant = letter == max(probs, key=probs.get)
            border = f"2px solid {sc['color_border']}" if is_dominant else \
                     f"0.5px solid {sc['color_border']}"
            st.markdown(
                f"""<div style='background:{sc["color_bg"]};border:{border};
                border-radius:10px;padding:12px;text-align:center;cursor:pointer'>
                  <div style='font-size:11px;color:{sc["color_text"]};font-weight:500;
                  text-transform:uppercase;letter-spacing:.05em'>{sc["name"][:12]}</div>
                  <div style='font-size:30px;font-weight:500;color:{sc["color_text"]}'>{prob}%</div>
                  <div style='font-size:11px;color:{sc["color_subtext"]}'>{sc["oil_range"]}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    if st.button("← Back to morning brief"):
        st.session_state["active_tab"] = "Morning Brief"
        st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render_signal_grid(signal_defs, statuses, prices, sparks,
                        show_only_active=False):
    """Render a 2-column grid of signal cards."""
    cols = st.columns(2)
    col_idx = 0

    for key, label, status_key, prefix, decimals, is_yield in signal_defs:
        sig    = statuses.get(status_key, {})
        raw    = get_current_value(prices, key, "price")

        # Yield from Yahoo comes as basis points
        if is_yield and raw is not None:
            raw = round(raw * 0.1, 2) if raw > 20 else raw

        status = sig.get("status", "normal")

        if show_only_active and status == "normal":
            continue

        col       = status_color(status)
        change    = get_current_value(prices, key, "change_pct")
        ytd       = get_current_value(prices, key, "ytd_pct")
        spark_data = sparks.get(key, [])

        # Threshold bar fill percentage
        thresh   = THRESHOLDS.get(status_key)
        fill_pct = _threshold_fill(raw, status_key) if thresh else 50

        change_color = "#3B6D11" if (change or 0) >= 0 else "#A32D2D"
        change_str   = format_pct(change)
        val_str      = f"{prefix}{raw:,.{decimals}f}" if raw is not None else "—"
        ytd_str      = f"YTD {format_pct(ytd)}" if ytd is not None else ""

        spark_json = json.dumps(spark_data)

        with cols[col_idx % 2]:
            # Inject sparkline via component HTML
            spark_id = f"spk_{key}_{col_idx}"
            st.markdown(
                f"""<div style='background:var(--background-color);
                border:.5px solid {col["border"]};border-radius:10px;
                padding:14px 16px;margin-bottom:10px;cursor:pointer'
                onclick='window.open("","_self")'>
                  <div style='display:flex;justify-content:space-between;align-items:center;
                  margin-bottom:6px'>
                    <span style='font-size:11px;font-weight:500;color:gray;
                    text-transform:uppercase;letter-spacing:.05em'>{label}</span>
                    <span style='background:{col["bg"]};color:{col["text"]};
                    border:.5px solid {col["border"]};border-radius:4px;
                    font-size:11px;padding:1px 7px;font-weight:500'>{col["label"]}</span>
                  </div>
                  <div style='font-size:22px;font-weight:500;margin-bottom:2px'>{val_str}</div>
                  <div style='font-size:12px;color:{change_color}'>{change_str} today
                  {' · ' + ytd_str if ytd_str else ''}</div>
                  <div style='height:3px;background:var(--secondary-background-color);
                  border-radius:2px;margin:10px 0 8px'>
                    <div style='height:100%;width:{fill_pct}%;background:{col["border"]};
                    border-radius:2px'></div></div>
                  <canvas id="{spark_id}" height="32" style="width:100%"></canvas>
                </div>
                <script>
                (function(){{
                  var data={spark_json};
                  var el=document.getElementById("{spark_id}");
                  if(!el||!data.length)return;
                  if(typeof Chart==="undefined"){{setTimeout(arguments.callee,200);return;}}
                  new Chart(el,{{type:"line",data:{{labels:data.map((_,i)=>i),datasets:[{{
                    data:data,borderColor:"{col["border"]}",borderWidth:1.5,
                    fill:false,pointRadius:0,tension:.3}}]}},
                  options:{{responsive:true,maintainAspectRatio:false,
                  plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}},
                  scales:{{x:{{display:false}},y:{{display:false}}}}}}}});
                }})();
                </script>""",
                unsafe_allow_html=True,
            )

        col_idx += 1


def _threshold_fill(value, signal_key):
    """Calculate fill % for the threshold progress bar (0–100)."""
    if value is None or signal_key not in THRESHOLDS:
        return 10
    t = THRESHOLDS[signal_key]

    # Map current value onto 0–100 scale between normal_lo and critical_hi
    normal_lo  = t["normal"][0]
    critical_hi = t["critical"][1] if t["critical"][1] < 999 else t["warning"][1] * 1.3

    if critical_hi <= normal_lo:
        return 50

    fill = ((value - normal_lo) / (critical_hi - normal_lo)) * 100
    return max(2, min(98, round(fill)))
