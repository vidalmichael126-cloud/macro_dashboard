"""
views/morning_brief.py — Dashboard C: The 30-second morning check.
Answers one question: has anything changed since yesterday, and what are today's rules?
Default tab — open this every morning before checking anything else.
"""

import streamlit as st
from datetime import datetime

from data_feeds import (
    fetch_live_prices,
    get_current_value,
    format_price,
    format_pct,
)
from signal_engine import (
    get_full_analysis,
    status_color,
    STATUS_COLORS,
    SEVERITY_COLORS,
)
from config import SCENARIOS


def render():
    analysis      = get_full_analysis()
    prices        = analysis["prices"]
    statuses      = analysis["statuses"]
    rules         = analysis["rules"]
    probs         = analysis["probs"]
    current_sc    = analysis["scenario"]
    sc_data       = SCENARIOS[current_sc]
    overnight     = analysis.get("overnight", {})
    open_est      = analysis.get("open_est", {})
    geo_score     = analysis.get("geo_score", {})
    ma_data       = analysis.get("ma_data", {})
    momentum      = analysis.get("momentum", {})

    now                = datetime.now()
    market_open        = 9 <= now.hour < 16
    pre_market_window  = now.hour >= 18 or now.hour < 9  # 6pm–9am overnight feed active

    # ── Header ────────────────────────────────────────────────────────────────
    col_date, col_time = st.columns([2, 1])
    with col_date:
        st.markdown(f"### Morning brief · {now.strftime('%a %b %d, %Y')}")
    with col_time:
        market_str = "Market open" if market_open else "Pre-market" if now.hour < 9 else "After hours"
        st.markdown(
            f"<div style='text-align:right;opacity:.6;font-size:13px;"
            f"padding-top:8px'>{now.strftime('%I:%M %p')} · {market_str}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Overnight intelligence feed (pre-market window only) ─────────────────
    if pre_market_window:
        _render_overnight_feed(overnight, open_est)
        st.divider()

    # ── Regime banner ─────────────────────────────────────────────────────────
    dominant_prob = probs[current_sc]
    st.markdown(
        f"""<div style='background:{sc_data["color_bg"]};
        border:1.5px solid {sc_data["color_border"]};
        border-radius:12px;padding:14px 18px;margin-bottom:14px;
        display:flex;align-items:center;justify-content:space-between'>
          <div>
            <div style='font-size:18px;font-weight:500;
            color:{sc_data["color_text"]}'>{sc_data["name"]}</div>
            <div style='font-size:13px;color:{sc_data["color_subtext"]};
            margin-top:3px'>{sc_data["description"]}</div>
          </div>
          <div style='text-align:right'>
            <div style='font-size:28px;font-weight:500;
            color:{sc_data["color_text"]}'>{dominant_prob}%</div>
            <div style='font-size:11px;color:{sc_data["color_subtext"]};
            text-transform:uppercase;letter-spacing:.05em'>probability</div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Pulse pills — quick glance at primary signals ─────────────────────────
    pulse_signals = [
        ("oil",      "Oil",     "$/bbl"),
        ("vix",      "VIX",     ""),
        ("usdjpy",   "USD/JPY", ""),
        ("yield_10", "10yr",    "%"),
    ]

    momentum_arrows = {"rising": " ↑", "falling": " ↓", "stable": ""}

    pill_parts = []
    for ticker_key, label, unit in pulse_signals:
        sig_info   = statuses.get(ticker_key, {})
        sig_val    = sig_info.get("value")
        sig_status = sig_info.get("status", "normal")
        sig_mom    = momentum.get(ticker_key, "stable")
        colors     = status_color(sig_status)
        val_str    = f"{sig_val:.2f}" if sig_val is not None else "—"
        arrow      = momentum_arrows.get(sig_mom, "")
        pill_parts.append(
            f"<span style='background:{colors['bg']};color:{colors['text']};"
            f"border:.5px solid {colors['border']};border-radius:20px;"
            f"padding:5px 12px;font-size:12px;font-weight:500'>"
            f"{label} {val_str}{unit}{arrow} · {colors['label'].lower()}</span>"
        )

    st.markdown(
        "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px'>"
        + "".join(pill_parts)
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Three key numbers ─────────────────────────────────────────────────────
    col_sp, col_gold, col_asia = st.columns(3)

    sp_chg   = get_current_value(prices, "sp500", "change_pct")
    gld_px   = get_current_value(prices, "gold",  "price")
    gld_ytd  = get_current_value(prices, "gold",  "ytd_pct")
    ewy_chg  = get_current_value(prices, "ewy",   "change_pct")

    with col_sp:
        _metric_tile(
            "S&P 500",
            format_pct(sp_chg),
            "pre-market" if not market_open else "today",
            sp_chg,
        )
    with col_gold:
        _metric_tile(
            "Gold (GLD)",
            format_price(gld_px),
            (format_pct(gld_ytd) + " YTD") if gld_ytd is not None else "—",
            gld_ytd,
        )
    with col_asia:
        _metric_tile(
            "Korea (EWY)",
            format_pct(ewy_chg),
            "Asia closed" if not market_open else "today",
            ewy_chg,
        )

    # ── New signal row: geo intensity + 200-day streak ────────────────────────
    col_geo, col_ma = st.columns(2)

    with col_geo:
        geo_val    = geo_score.get("score", 0)
        geo_status = geo_score.get("status", "normal")
        geo_colors = status_color(geo_status)
        st.markdown(
            f"<div style='background:{geo_colors['bg']};border:.5px solid {geo_colors['border']};"
            f"border-radius:8px;padding:10px 14px;text-align:center'>"
            f"<div style='font-size:11px;color:{geo_colors['text']};opacity:.7;margin-bottom:2px'>Geopolitical intensity</div>"
            f"<div style='font-size:22px;font-weight:500;color:{geo_colors['text']}'>{geo_val}<span style='font-size:13px'>/100</span></div>"
            f"<div style='font-size:11px;color:{geo_colors['text']};opacity:.7'>{geo_status}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_ma:
        above   = ma_data.get("above_200d")
        streak  = ma_data.get("streak_days", 0)
        pct     = ma_data.get("pct_from_ma", 0)
        if above is not None:
            ma_color = "#27500A" if above else "#791F1F"
            ma_bg    = "#EAF3DE" if above else "#FCEBEB"
            ma_border= "#639922" if above else "#E24B4A"
            state_str= f"{'above' if above else 'BELOW'} 200-day"
            st.markdown(
                f"<div style='background:{ma_bg};border:.5px solid {ma_border};"
                f"border-radius:8px;padding:10px 14px;text-align:center'>"
                f"<div style='font-size:11px;color:{ma_color};opacity:.7;margin-bottom:2px'>S&P vs 200-day MA</div>"
                f"<div style='font-size:22px;font-weight:500;color:{ma_color}'>{streak}d <span style='font-size:13px'>{state_str}</span></div>"
                f"<div style='font-size:11px;color:{ma_color};opacity:.7'>{pct:+.1f}% from MA</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<div style='padding:10px 14px;font-size:12px;color:gray'>200-day data unavailable</div>", unsafe_allow_html=True)

    st.divider()

    # ── Active combination rules ───────────────────────────────────────────────
    active_rules   = [r for r in rules if r.get("state") == "active"]
    watching_rules = [r for r in rules if r.get("state") == "watch"]

    if active_rules:
        st.markdown("**Active signal combinations**")
        for rule in active_rules:
            severity = rule.get("severity", "warning")
            colors   = SEVERITY_COLORS.get(severity, STATUS_COLORS["warning"])
            st.markdown(
                f"""<div style='background:{colors["bg"]};
                border:.5px solid {colors["border"]};
                border-radius:8px;padding:10px 14px;margin-bottom:8px'>
                  <div style='font-weight:500;color:{colors["text"]};
                  font-size:13px'>{rule["name"]}</div>
                  <div style='font-size:12px;color:{colors["text"]};
                  opacity:.85;margin-top:3px'>{rule["description"]}</div>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div style='background:var(--secondary-background-color);"
            "border-radius:8px;padding:10px 14px;font-size:13px;"
            "color:gray;text-align:center;margin-bottom:8px'>"
            "No combination rules firing right now</div>",
            unsafe_allow_html=True,
        )

    for rule in watching_rules[:2]:
        missing_str = ", ".join(rule.get("missing", []))
        st.markdown(
            f"""<div style='background:{STATUS_COLORS["elevated"]["bg"]};
            border:.5px solid {STATUS_COLORS["elevated"]["border"]};
            border-radius:8px;padding:8px 14px;margin-bottom:6px'>
              <div style='font-weight:500;color:{STATUS_COLORS["elevated"]["text"]};
              font-size:13px'>{rule["name"]} — watch</div>
              <div style='font-size:12px;color:{STATUS_COLORS["elevated"]["text"]};
              opacity:.8;margin-top:2px'>Needs: {missing_str or "one more threshold"}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Today's decision rules ─────────────────────────────────────────────────
    st.markdown("**Today's rules**")

    for action in sc_data["actions"]:
        icon, icon_style = _action_icon_style(action)
        st.markdown(
            f"""<div style='display:flex;align-items:flex-start;gap:10px;
            padding:9px 0;border-bottom:.5px solid rgba(128,128,128,.12)'>
              <div style='width:22px;height:22px;border-radius:4px;
              {icon_style}display:flex;align-items:center;justify-content:center;
              font-size:11px;font-weight:500;flex-shrink:0;margin-top:1px'>{icon}</div>
              <div style='font-size:13px;line-height:1.5;flex:1'>{action}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Footer navigation ──────────────────────────────────────────────────────
    btn_sig, btn_reg, btn_refresh = st.columns(3)

    with btn_sig:
        if st.button("Signal board ↗", use_container_width=True):
            st.session_state["active_tab"] = "Signal Board"
            st.rerun()
    with btn_reg:
        if st.button("Regime board ↗", use_container_width=True):
            st.session_state["active_tab"] = "Regime Board"
            st.rerun()
    with btn_refresh:
        if st.button("Refresh data ↺", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _metric_tile(label: str, value: str, sub: str, direction_value):
    """Render a single metric tile with directional color coding."""
    if direction_value is None:
        color = "gray"
    elif direction_value >= 0:
        color = "#3B6D11"
    else:
        color = "#A32D2D"

    st.markdown(
        f"""<div style='background:var(--secondary-background-color);
        border-radius:8px;padding:12px 14px;text-align:center'>
          <div style='font-size:11px;color:gray;margin-bottom:3px'>{label}</div>
          <div style='font-size:20px;font-weight:500;color:{color}'>{value}</div>
          <div style='font-size:11px;color:gray;margin-top:2px'>{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def _action_icon_style(action_text: str) -> tuple:
    """Return (icon_char, inline_css) based on the intent of an action string."""
    text_lower = action_text.lower()
    if any(w in text_lower for w in ["hold", "continue", "no change", "steady", "never"]):
        return "—", "background:#EAF3DE;color:#27500A;"
    elif any(w in text_lower for w in ["watch", "monitor", "approaching"]):
        return "!", "background:#FAEEDA;color:#633806;"
    elif any(w in text_lower for w in ["sell", "reduce", "exit", "avoid", "take profits"]):
        return "↓", "background:#FCEBEB;color:#791F1F;"
    elif any(w in text_lower for w in ["add", "buy", "increase", "rotate", "max"]):
        return "+", "background:#E6F1FB;color:#0C447C;"
    else:
        return "→", "background:var(--secondary-background-color);color:gray;"


def _render_overnight_feed(overnight: dict, open_est: dict):
    """
    Overnight intelligence feed — shown during 6pm–9:30am EST window.
    Displays Asia close, European open, overnight oil trend,
    and the predictive S&P 500 open estimate.
    """
    st.markdown("**Overnight intelligence · Pre-market feed**")

    estimate   = open_est.get("estimate")
    direction  = open_est.get("direction", "unknown")
    details    = open_est.get("details", [])

    # Open estimate banner
    if estimate is not None:
        est_color  = "#27500A" if estimate > 0.1 else "#791F1F" if estimate < -0.1 else "#633806"
        est_bg     = "#EAF3DE" if estimate > 0.1 else "#FCEBEB" if estimate < -0.1 else "#FAEEDA"
        est_border = "#639922" if estimate > 0.1 else "#E24B4A" if estimate < -0.1 else "#EF9F27"
        arrow      = "↑" if estimate > 0.1 else "↓" if estimate < -0.1 else "→"

        st.markdown(
            f"<div style='background:{est_bg};border:1.5px solid {est_border};"
            f"border-radius:10px;padding:12px 16px;margin-bottom:10px'>"
            f"<div style='font-size:13px;font-weight:500;color:{est_color}'>"
            f"{arrow} Model estimates S&P opens {direction} · {estimate:+.2f}%</div>"
            f"<div style='font-size:11px;color:{est_color};opacity:.8;margin-top:4px'>"
            + " &nbsp;|&nbsp; ".join(details)
            + "</div>"
            f"<div style='font-size:10px;color:{est_color};opacity:.6;margin-top:4px'>"
            f"Coefficients: KOSPI→0.25, Nikkei→0.18, Europe→0.30 · Hardcoded from March 2026 conflict week · Refine after 30+ data points"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # Asia + Europe signal row
    cols = st.columns(4)
    overnight_items = [
        ("ewy",          "KOSPI (EWY)",   "Korea"),
        ("ewj",          "Nikkei (EWJ)",  "Japan"),
        ("fez",          "Stoxx (FEZ)",   "Europe"),
        ("oil_overnight","WTI 6h trend",  "Oil"),
    ]

    for i, (key, label, region) in enumerate(overnight_items):
        data = overnight.get(key, {})
        with cols[i]:
            if data.get("ok"):
                if key == "oil_overnight":
                    val  = data.get("price", 0)
                    chg  = data.get("trend_6h", 0)
                    disp = f"${val:.2f}"
                    sub  = f"6h: {chg:+.1f}%"
                else:
                    chg  = data.get("change_pct", 0)
                    disp = f"{chg:+.1f}%"
                    sub  = region

                color = "#3B6D11" if (chg or 0) >= 0 else "#A32D2D"
                st.markdown(
                    f"<div style='background:var(--secondary-background-color);"
                    f"border-radius:7px;padding:8px 10px;text-align:center'>"
                    f"<div style='font-size:10px;color:gray;margin-bottom:2px'>{label}</div>"
                    f"<div style='font-size:16px;font-weight:500;color:{color}'>{disp}</div>"
                    f"<div style='font-size:10px;color:gray'>{sub}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background:var(--secondary-background-color);"
                    f"border-radius:7px;padding:8px 10px;text-align:center'>"
                    f"<div style='font-size:10px;color:gray;margin-bottom:2px'>{label}</div>"
                    f"<div style='font-size:14px;color:gray'>—</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
