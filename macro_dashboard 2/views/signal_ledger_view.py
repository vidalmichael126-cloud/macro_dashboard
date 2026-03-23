"""
views/signal_ledger_view.py — Primary signal display.
Replaces morning_brief + signal_board with the new ledger design.
"""

import streamlit as st
from datetime import datetime
from signal_engine import get_full_analysis, status_color, STATUS_COLORS
from data_feeds import get_current_value, format_price, format_pct
from config import THRESHOLDS


def _status_pill(status, label=None):
    c = STATUS_COLORS.get(status, STATUS_COLORS["normal"])
    txt = label or c["label"]
    return (
        f"<span style='background:{c['bg']};color:{c['text']};"
        f"border:0.5px solid {c['border']};border-radius:4px;"
        f"padding:2px 8px;font-size:10px;font-weight:500'>{txt}</span>"
    )


def _momentum_arrow(mom):
    return {"rising":"↑","falling":"↓","stable":"→"}.get(mom,"")


def _bar(pct, color):
    return (
        f"<div style='height:3px;background:#eee;border-radius:2px;margin:6px 0'>"
        f"<div style='height:100%;width:{min(100,max(0,pct))}%;background:{color};"
        f"border-radius:2px'></div></div>"
    )


def _signal_row(key, label, value_str, status, mom, bar_pct, bar_color,
                expand_content=None):
    c = STATUS_COLORS.get(status, STATUS_COLORS["normal"])
    arrow = _momentum_arrow(mom)

    with st.expander(
        f"{label}  ·  {value_str}  {arrow}",
        expanded=False,
    ):
        col_v, col_s = st.columns([3, 1])
        with col_v:
            st.markdown(
                f"<div style='font-size:22px;font-weight:500;color:{c['text']}'>"
                f"{value_str} <span style='font-size:13px'>{arrow}</span></div>"
                f"{_bar(bar_pct, bar_color)}"
                f"{_status_pill(status)}",
                unsafe_allow_html=True,
            )
        with col_s:
            pass

        if expand_content:
            st.markdown("---")
            st.markdown(expand_content, unsafe_allow_html=True)


def render():
    analysis = get_full_analysis()
    prices   = analysis["prices"]
    statuses = analysis["statuses"]
    momentum = analysis["momentum"]
    ma_data  = analysis["ma_data"]
    geo      = analysis["geo_score"]
    overnight = analysis.get("overnight", {})
    open_est  = analysis.get("open_est", {})
    gold_data = analysis.get("gold_data", {})
    pe_data   = analysis.get("pe_data", {})
    hyg_data  = analysis.get("hyg_data", {})
    jp10y_data = analysis.get("jp10y_data", {})

    now = datetime.now()
    is_premarket = now.hour < 9 or now.hour >= 18

    # ── Overnight banner ──────────────────────────────────────────────────────
    if is_premarket and open_est.get("estimate") is not None:
        est = open_est["estimate"]
        direction = open_est.get("direction","flat")
        arrow = "↑" if est > 0.1 else "↓" if est < -0.1 else "→"
        color = "#27500A" if est > 0 else "#791F1F"
        bg    = "#EAF3DE" if est > 0 else "#FCEBEB"
        st.markdown(
            f"<div style='background:{bg};border:1px solid;border-radius:10px;"
            f"padding:10px 14px;margin-bottom:12px'>"
            f"<div style='font-size:13px;font-weight:500;color:{color}'>"
            f"{arrow} Model estimates S&P opens {direction} · {est:+.2f}%</div>"
            f"<div style='font-size:11px;color:{color};opacity:.75;margin-top:3px'>"
            f"{'  |  '.join(open_est.get('details',[]))}</div>"
            f"<div style='font-size:10px;color:{color};opacity:.55;margin-top:3px'>"
            f"Coefficients: KOSPI 0.25 · Nikkei 0.18 · Europe 0.30 · hardcoded Mar 2026</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Asian market tiles
        cols = st.columns(4)
        overnight_items = [
            ("ewy","KOSPI (EWY)"),("ewj","Nikkei (EWJ)"),
            ("fez","Europe (FEZ)"),("oil_overnight","WTI 6h"),
        ]
        for col, (key, label) in zip(cols, overnight_items):
            data = overnight.get(key, {})
            with col:
                if data.get("ok"):
                    if key == "oil_overnight":
                        val = f"${data.get('price',0):.2f}"
                        chg = data.get("trend_6h",0)
                    else:
                        chg = data.get("change_pct",0)
                        val = f"{chg:+.1f}%"
                    color = "#27500A" if (chg or 0) >= 0 else "#791F1F"
                    st.metric(label, val)
                else:
                    st.metric(label, "—")

        st.divider()

    # ── Primary signals ───────────────────────────────────────────────────────
    st.markdown("**Primary signals** — tap to expand reasoning")

    SIGNALS = [
        ("oil",     "WTI crude oil",    "price",  "$/bbl", 0,   150, "#EF9F27"),
        ("vix",     "VIX",              "price",  "",      0,   40,  "#EF9F27"),
        ("yield_10","10yr Treasury",    "price",  "%",     4.0, 5.5, "#EF9F27"),
        ("usdjpy",  "USD / JPY",        "price",  "",      145, 158, "#EF9F27"),
    ]

    for sig_key, label, field, unit, lo, hi, bar_col in SIGNALS:
        sig   = statuses.get(sig_key, {})
        val   = sig.get("value")
        status = sig.get("status","normal")
        mom   = momentum.get(sig_key,"stable")
        note  = sig.get("note","")
        thresholds = THRESHOLDS.get(sig_key,{})

        # Bar: position within relevant range
        bar_pct = max(0, min(100, ((val or lo) - lo) / (hi - lo) * 100)) if val else 0

        val_str = f"{val:.2f}{unit}" if val else "—"

        # Connected signals from config note
        connected = ", ".join(
            [r["name"] for r in analysis.get("rules",[])
             if sig_key in r.get("connected_signals",[])][:4]
        ) or "—"

        detail = (
            f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:11px'>"
            f"<div><div style='font-size:9px;font-weight:600;letter-spacing:.06em;"
            f"text-transform:uppercase;color:gray;margin-bottom:3px'>What crossed</div>"
            f"{note}</div>"
            f"<div><div style='font-size:9px;font-weight:600;letter-spacing:.06em;"
            f"text-transform:uppercase;color:gray;margin-bottom:3px'>Connected to</div>"
            f"{connected}</div>"
            f"</div>"
        )

        _signal_row(sig_key, label, val_str, status, mom, bar_pct, bar_col, detail)

    # ── 200-day MA ────────────────────────────────────────────────────────────
    if ma_data.get("ok"):
        above  = ma_data.get("above_200d", True)
        streak = ma_data.get("streak_days", 0)
        pct    = ma_data.get("pct_from_ma", 0)
        status = "critical" if not above else "normal"
        val_str = f"{'Above' if above else 'BELOW'} · {streak}d streak"
        detail = (
            f"<div style='font-size:11px'>"
            f"S&P at {ma_data.get('current_price','?')} vs 200-day MA at {ma_data.get('ma_200','?')}.<br>"
            f"{pct:+.1f}% from MA · {'Institutional algos in sell mode' if not above else 'Support intact'}</div>"
        )
        _signal_row("ma200", "S&P 200-day MA", val_str, status, "stable", 100 if not above else 0, "#E24B4A" if not above else "#639922", detail)

    # ── Burry engine signals ──────────────────────────────────────────────────
    st.markdown("**Burry engine signals**")

    # HYG
    if hyg_data.get("ok"):
        ret = hyg_data.get("hyg_5d_ret", 0)
        status = hyg_data.get("status","normal")
        bar_pct = max(0, min(100, abs(ret) / 3 * 100)) if ret < 0 else 0
        detail = (
            f"<div style='font-size:11px'>"
            f"HYG 5-day return: {ret:+.2f}%<br>"
            f"Entry threshold: &lt;−1.5% · Currently {ret-(-1.5):+.2f}% from trigger<br>"
            f"Consecutive down days: {hyg_data.get('consecutive_down',0)}<br>"
            f"Role: Stream 1 of 2 for HYG puts Burry entry</div>"
        )
        _signal_row("hyg","HYG credit stress", f"{ret:+.2f}% 5d", status, "falling" if ret < 0 else "stable", bar_pct, "#E24B4A", detail)

    # PE basket
    if pe_data.get("ok"):
        spread = pe_data.get("spread",0)
        status = pe_data.get("status","normal")
        bar_pct = max(0, min(100, abs(spread) / 8 * 100)) if spread < 0 else 0
        ind = pe_data.get("individual",{})
        ind_str = " · ".join(f"{t}: {v.get('return_10d',0):+.1f}%" for t,v in ind.items() if v.get("ok"))
        detail = (
            f"<div style='font-size:11px'>"
            f"Basket vs SPY 10d: {spread:+.2f}%<br>"
            f"Entry threshold: &lt;−5% · Currently {spread-(-5):+.2f}% from trigger<br>"
            f"Individual: {ind_str}<br>"
            f"Role: Stream 2 of 2 for HYG puts Burry entry</div>"
        )
        _signal_row("pe","PE basket vs SPY", f"{spread:+.2f}% 10d", status, "falling" if spread < 0 else "stable", bar_pct, "#E24B4A", detail)

    # Gold tracker
    if gold_data.get("ok"):
        ret60 = gold_data.get("ret_60d") or 0
        status = gold_data.get("status","normal")
        bar_pct = min(100, ret60 / 40 * 100) if ret60 > 0 else 0
        note = gold_data.get("analog_note","")
        detail = f"<div style='font-size:11px'>{note}<br>Pullback from high: {gold_data.get('pct_from_high',0):+.1f}%</div>"
        _signal_row("gold","Gold 1979 tracker", f"+{ret60:.0f}% 60d", status, "rising", bar_pct, "#d4a847", detail)

    # Japan JGB
    if jp10y_data.get("ok"):
        jp10y = jp10y_data.get("jp10y",0)
        status = jp10y_data.get("status","normal")
        bar_pct = min(100, jp10y / 1.2 * 100)
        detail = (
            f"<div style='font-size:11px'>"
            f"JP10Y: {jp10y:.3f}% · BoJ soft cap: 1.0% · Gap: {jp10y-1.0:+.3f}%<br>"
            f"Mechanism: JGB rises → BoJ sells Treasuries → US 10yr spikes → Sell America</div>"
        )
        _signal_row("jp10y","Japan JGB (JP10Y)", f"{jp10y:.3f}%", status, "rising" if jp10y_data.get("change_bps",0) > 0 else "stable", bar_pct, "#534AB7", detail)
