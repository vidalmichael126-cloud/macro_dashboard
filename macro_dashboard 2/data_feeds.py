"""
data_feeds.py — All data fetching in one place.
Uses yfinance for market data, FRED for macro series.
Caches aggressively to avoid hammering free APIs.
"""

import yfinance as yf
import pandas as pd
import requests
import streamlit as st
from datetime import datetime, timedelta
from config import YAHOO_TICKERS, FRED_SERIES, FRED_BASE, SPARKLINE_DAYS, REFRESH_INTERVALS


# ─── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_ttl():
    """Return cache TTL in seconds based on config."""
    return REFRESH_INTERVALS["cache_hours"] * 3600


@st.cache_data(ttl=900)   # 15-minute cache for intraday signals
def fetch_live_prices() -> dict:
    """
    Fetch current prices and daily changes for all tracked tickers.
    Returns a flat dict: { "oil": {"price": 98.71, "change_pct": 3.1, ...}, ... }
    Falls back gracefully on individual ticker failures.
    """
    results = {}

    for name, ticker in YAHOO_TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d")

            if hist.empty or len(hist) < 2:
                results[name] = _empty_price(ticker)
                continue

            latest_close  = hist["Close"].iloc[-1]
            prev_close    = hist["Close"].iloc[-2]
            change_pct    = ((latest_close - prev_close) / prev_close) * 100
            change_abs    = latest_close - prev_close

            # YTD change
            ytd_start = datetime(datetime.now().year, 1, 1)
            hist_ytd  = t.history(start=ytd_start.strftime("%Y-%m-%d"))
            ytd_pct   = 0.0
            if not hist_ytd.empty:
                first_price = hist_ytd["Close"].iloc[0]
                ytd_pct = ((latest_close - first_price) / first_price) * 100

            # 52-week high
            hist_52w  = t.history(period="52wk")
            high_52w  = hist_52w["High"].max() if not hist_52w.empty else latest_close
            pct_from_high = ((latest_close - high_52w) / high_52w) * 100

            results[name] = {
                "ticker":         ticker,
                "price":          round(latest_close, 2),
                "change_pct":     round(change_pct, 2),
                "change_abs":     round(change_abs, 2),
                "ytd_pct":        round(ytd_pct, 1),
                "high_52w":       round(high_52w, 2),
                "pct_from_high":  round(pct_from_high, 1),
                "timestamp":      hist.index[-1].strftime("%Y-%m-%d %H:%M"),
                "ok":             True,
            }

        except Exception as e:
            results[name] = _empty_price(ticker, error=str(e))

    return results


@st.cache_data(ttl=900)
def fetch_sparklines() -> dict:
    """
    Fetch N days of closing prices for sparkline charts.
    Returns { ticker_name: [price1, price2, ...] }
    """
    sparklines = {}
    period = f"{SPARKLINE_DAYS}d"

    for name, ticker in YAHOO_TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if not hist.empty:
                prices = [round(p, 2) for p in hist["Close"].tolist()]
                sparklines[name] = prices
            else:
                sparklines[name] = []
        except Exception:
            sparklines[name] = []

    return sparklines


@st.cache_data(ttl=_cache_ttl())
def fetch_fred_series(series_id: str, days: int = 90) -> pd.Series:
    """
    Fetch a FRED series as a pandas Series indexed by date.
    Returns empty Series on failure — never crashes the app.
    """
    try:
        url = f"{FRED_BASE}{series_id}"
        df  = pd.read_csv(url, parse_dates=["DATE"], index_col="DATE")
        df  = df.replace(".", float("nan")).dropna()
        df  = df[df.index >= pd.Timestamp.now() - pd.Timedelta(days=days)]
        df.columns = [series_id]
        series = df[series_id].astype(float)
        return series
    except Exception:
        return pd.Series(dtype=float, name=series_id)


@st.cache_data(ttl=_cache_ttl())
def fetch_all_fred() -> dict:
    """
    Fetch all FRED macro series defined in config.
    Returns { series_name: pd.Series }
    """
    return {name: fetch_fred_series(sid) for name, sid in FRED_SERIES.items()}


@st.cache_data(ttl=3600)
def fetch_yield_curve_history(days: int = 60) -> pd.DataFrame:
    """
    Fetch 2-year and 10-year yields together for curve analysis.
    Returns DataFrame with columns: yield_2yr, yield_10yr, spread
    """
    try:
        s2  = fetch_fred_series(FRED_SERIES["yield_2yr"],  days=days)
        s10 = fetch_fred_series(FRED_SERIES["yield_10yr"], days=days)

        df = pd.DataFrame({"yield_2yr": s2, "yield_10yr": s10})
        df = df.dropna()
        df["spread"] = df["yield_10yr"] - df["yield_2yr"]
        return df
    except Exception:
        return pd.DataFrame(columns=["yield_2yr", "yield_10yr", "spread"])


def get_current_value(prices: dict, key: str, field: str = "price"):
    """Safe getter — returns None if key or field missing."""
    if key not in prices:
        return None
    entry = prices[key]
    if not entry.get("ok", False):
        return None
    return entry.get(field)


def get_xle_oil_divergence(prices: dict) -> dict:
    """
    Check whether XLE is diverging from oil (falling while oil stays high).
    This is the Simons-style early peace signal — historically precedes
    oil price peaks by 3–6 weeks.
    Returns: { "diverging": bool, "xle_change": float, "oil_change": float, "note": str }
    """
    oil_chg = get_current_value(prices, "oil",  "change_pct")
    xle_chg = get_current_value(prices, "xle",  "change_pct")
    oil_px  = get_current_value(prices, "oil",  "price")

    if oil_chg is None or xle_chg is None or oil_px is None:
        return {"diverging": False, "xle_change": 0, "oil_change": 0,
                "note": "Insufficient data"}

    # Divergence = oil flat/up AND xle falling, while oil > $90
    diverging = (
        oil_px  > 90
        and xle_chg < -1.0    # XLE down more than 1%
        and oil_chg > -1.0    # Oil not also falling
    )

    note = ""
    if diverging:
        note = (f"XLE −{abs(xle_chg):.1f}% while oil {'+' if oil_chg >= 0 else ''}"
                f"{oil_chg:.1f}% — early resolution signal. Historical lead: 3–6 weeks.")
    else:
        gap = xle_chg - oil_chg
        note = f"No divergence. XLE/Oil gap: {gap:+.1f}%"

    return {
        "diverging":    diverging,
        "xle_change":   round(xle_chg, 2),
        "oil_change":   round(oil_chg, 2),
        "note":         note,
    }


def get_dollar_falling(prices: dict) -> bool:
    """Check if dollar is meaningfully falling today."""
    # DXY not directly in Yahoo as a clean ticker, so we proxy via:
    # EUR/USD rising = dollar falling
    # We can also use the FRED DXY series for yesterday's close
    fred = fetch_all_fred()
    dxy  = fred.get("dxy")
    if dxy is None or len(dxy) < 2:
        return False
    # Dollar falling = latest value below previous
    return float(dxy.iloc[-1]) < float(dxy.iloc[-2])


@st.cache_data(ttl=900)
def get_200day_ma() -> dict:
    """
    Fetch SPY 200-day moving average and current streak above/below it.
    Returns: {
        "ma_200":        float,   # Current 200-day MA value
        "current_price": float,   # Latest SPY close
        "above_200d":    bool,    # True if price above MA
        "streak_days":   int,     # Consecutive days above (positive) or below (negative)
        "pct_from_ma":   float,   # % above/below the MA
    }
    """
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="300d")
        if len(hist) < 200:
            return _empty_200d()

        closes = hist["Close"]
        ma200  = closes.rolling(200).mean()

        current_price = float(closes.iloc[-1])
        current_ma    = float(ma200.iloc[-1])
        above         = current_price > current_ma
        pct_from_ma   = ((current_price - current_ma) / current_ma) * 100

        # Count consecutive days in current state
        streak = 0
        for i in range(len(closes) - 1, -1, -1):
            price = float(closes.iloc[i])
            ma    = float(ma200.iloc[i])
            if pd.isna(ma):
                break
            if (price > ma) == above:
                streak += 1
            else:
                break

        return {
            "ma_200":        round(current_ma, 2),
            "current_price": round(current_price, 2),
            "above_200d":    above,
            "streak_days":   streak,
            "pct_from_ma":   round(pct_from_ma, 2),
            "ok":            True,
        }
    except Exception as e:
        return _empty_200d(error=str(e))


@st.cache_data(ttl=900)
def get_overnight_signals() -> dict:
    """
    Fetch overnight data for the pre-market intelligence feed.
    Returns Asia close + European open + overnight oil trend.
    Active window: 6pm–9:30am EST (when US market is closed).
    """
    results = {}

    # Asia proxies (EWY = Korea, EWJ = Japan)
    for key in ["ewy", "ewj", "fez"]:
        ticker = {"ewy": "EWY", "ewj": "EWJ", "fez": "FEZ"}[key]
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                latest = float(hist["Close"].iloc[-1])
                prev   = float(hist["Close"].iloc[-2])
                chg    = ((latest - prev) / prev) * 100
                results[key] = {"price": round(latest, 2), "change_pct": round(chg, 2), "ok": True}
            else:
                results[key] = {"ok": False}
        except Exception:
            results[key] = {"ok": False}

    # Overnight oil — 5-day hourly to get recent direction
    try:
        oil  = yf.Ticker("CL=F")
        hist = oil.history(period="2d", interval="1h")
        if len(hist) >= 6:
            latest    = float(hist["Close"].iloc[-1])
            six_ago   = float(hist["Close"].iloc[-6])
            trend_pct = ((latest - six_ago) / six_ago) * 100
            results["oil_overnight"] = {
                "price":     round(latest, 2),
                "trend_6h":  round(trend_pct, 2),
                "ok":        True,
            }
        else:
            results["oil_overnight"] = {"ok": False}
    except Exception:
        results["oil_overnight"] = {"ok": False}

    return results


@st.cache_data(ttl=1800)
def get_signal_momentum(days: int = 3) -> dict:
    """
    Compute 3-day directional momentum for primary signals.
    Returns { signal_key: "rising" | "falling" | "stable" }
    A signal is rising/falling if the N-day slope exceeds a minimum threshold.
    """
    momentum = {}
    ticker_map = {
        "oil":      ("CL=F",  1.5),   # $1.50/barrel minimum move to count
        "vix":      ("^VIX",  0.5),   # 0.5 VIX points
        "yield_10": ("^TNX",  0.05),  # 5 basis points
        "usdjpy":   ("JPY=X", 0.3),   # 0.3 yen
        "sp500":    ("^GSPC", 15.0),  # 15 S&P points
    }

    for signal, (ticker, min_move) in ticker_map.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period=f"{days + 3}d")
            if len(hist) < days + 1:
                momentum[signal] = "stable"
                continue

            recent = float(hist["Close"].iloc[-1])
            past   = float(hist["Close"].iloc[-(days + 1)])
            delta  = recent - past

            # Yield fix: ^TNX returns in basis points
            if signal == "yield_10" and recent > 20:
                recent = recent * 0.1
                past   = past   * 0.1
                delta  = recent - past

            if delta > min_move:
                momentum[signal] = "rising"
            elif delta < -min_move:
                momentum[signal] = "falling"
            else:
                momentum[signal] = "stable"

        except Exception:
            momentum[signal] = "stable"

    return momentum


@st.cache_data(ttl=900)
def get_iwm_spy_ratio() -> dict:
    """
    Compute IWM/SPY relative performance over 5 days.
    Small caps underperforming large caps = credit stress / recession pricing.
    Returns: { "ratio_5d": float, "underperforming": bool, "magnitude": float }
    """
    try:
        iwm_hist = yf.Ticker("IWM").history(period="10d")
        spy_hist = yf.Ticker("SPY").history(period="10d")

        if len(iwm_hist) < 5 or len(spy_hist) < 5:
            return {"ok": False}

        iwm_ret = (float(iwm_hist["Close"].iloc[-1]) / float(iwm_hist["Close"].iloc[-5]) - 1) * 100
        spy_ret = (float(spy_hist["Close"].iloc[-1]) / float(spy_hist["Close"].iloc[-5]) - 1) * 100
        spread  = iwm_ret - spy_ret  # negative = small caps underperforming

        return {
            "iwm_5d_ret":      round(iwm_ret, 2),
            "spy_5d_ret":      round(spy_ret, 2),
            "spread":          round(spread, 2),
            "underperforming": spread < -2.0,  # IWM lagging SPY by 2%+ = recession signal
            "ok":              True,
        }
    except Exception:
        return {"ok": False}


# ─── New: PE basket ───────────────────────────────────────────────────────────

@st.cache_data(ttl=900)
def get_pe_basket() -> dict:
    """
    Compute equal-weight PE basket (BX/KKR/APO/ARES/OWL) vs SPY
    over 10 trading days. This is the Burry PE short confirmation signal.

    Returns: {
        "basket_10d_ret":  float,   # equal-weight basket 10d return
        "spy_10d_ret":     float,   # SPY 10d return same window
        "spread":          float,   # basket minus SPY (negative = PE lagging)
        "status":          str,     # "normal" | "elevated" | "warning" | "critical"
        "individual":      dict,    # per-ticker 10d returns
        "ok":              bool,
    }
    """
    from config import PE_BASKET, THRESHOLDS
    tickers  = PE_BASKET["tickers"]
    lookback = PE_BASKET["lookback_days"]
    period   = f"{lookback + 5}d"   # buffer for weekends/holidays

    individual = {}
    returns    = []

    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if len(hist) < lookback:
                individual[ticker] = {"ok": False}
                continue
            ret = (float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[-lookback]) - 1) * 100
            individual[ticker] = {"return_10d": round(ret, 2), "ok": True}
            returns.append(ret)
        except Exception as e:
            individual[ticker] = {"ok": False, "error": str(e)}

    if not returns:
        return {"ok": False, "individual": individual}

    basket_ret = round(sum(returns) / len(returns), 2)

    # SPY for comparison
    try:
        spy_hist   = yf.Ticker("SPY").history(period=period)
        spy_ret    = round(
            (float(spy_hist["Close"].iloc[-1]) / float(spy_hist["Close"].iloc[-lookback]) - 1) * 100, 2
        ) if len(spy_hist) >= lookback else 0.0
    except Exception:
        spy_ret = 0.0

    spread = round(basket_ret - spy_ret, 2)   # negative = PE underperforming

    # Map spread to status using threshold config
    thresholds = THRESHOLDS["pe_vs_spy_10d"]
    if   spread <= thresholds["critical"][0]:   status = "critical"
    elif spread <= thresholds["warning"][0]:    status = "warning"
    elif spread <= thresholds["elevated"][0]:   status = "elevated"
    else:                                       status = "normal"

    return {
        "basket_10d_ret": basket_ret,
        "spy_10d_ret":    spy_ret,
        "spread":         spread,
        "status":         status,
        "individual":     individual,
        "lagging":        spread <= PE_BASKET["lag_threshold_pct"],
        "ok":             True,
    }


# ─── New: HYG credit stress ────────────────────────────────────────────────────

@st.cache_data(ttl=900)
def get_hyg_credit_stress() -> dict:
    """
    Score HYG 5-day return as a credit stress signal.
    HYG falling = high-yield credit spreads widening = PE debt costs rising.

    This is independent of the PE basket — two independent streams
    must confirm before firing the Burry PE short entry signal.

    Returns: {
        "hyg_5d_ret":  float,   # 5-day return %
        "hyg_1d_ret":  float,   # yesterday's move
        "status":      str,     # normal / elevated / warning / critical
        "consecutive_down": int, # days consecutively negative
        "ok":          bool,
    }
    """
    from config import THRESHOLDS
    try:
        hist = yf.Ticker("HYG").history(period="15d")
        if len(hist) < 6:
            return {"ok": False}

        latest     = float(hist["Close"].iloc[-1])
        five_ago   = float(hist["Close"].iloc[-6])
        prev       = float(hist["Close"].iloc[-2])

        ret_5d = round((latest - five_ago) / five_ago * 100, 2)
        ret_1d = round((latest - prev)     / prev     * 100, 2)

        # Count consecutive down days
        consecutive_down = 0
        for i in range(len(hist) - 1, 0, -1):
            if hist["Close"].iloc[i] < hist["Close"].iloc[i - 1]:
                consecutive_down += 1
            else:
                break

        # Map to status
        t = THRESHOLDS["hyg_5d"]
        if   ret_5d <= t["critical"][0]:  status = "critical"
        elif ret_5d <= t["warning"][0]:   status = "warning"
        elif ret_5d <= t["elevated"][0]:  status = "elevated"
        else:                             status = "normal"

        return {
            "hyg_5d_ret":      ret_5d,
            "hyg_1d_ret":      ret_1d,
            "hyg_price":       round(latest, 2),
            "status":          status,
            "consecutive_down": consecutive_down,
            "ok":              True,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── New: Gold 1979 parabolic tracker ─────────────────────────────────────────

@st.cache_data(ttl=1800)
def get_gold_tracker() -> dict:
    """
    Track gold's trajectory against the 1979 Iranian Revolution parabolic.

    Three lookback windows: 30d, 60d, 90d.
    Fires:
      - "pattern_active"  when 60d change > 25%  (accumulation phase, add on dips)
      - "reversal_risk"   when 60d change > 40%  (exit signal — 1979 ended here)

    Also computes: pullback from recent high (add zone = 8–12% below high).

    Returns: {
        "ret_30d":          float,
        "ret_60d":          float,
        "ret_90d":          float,
        "recent_high":      float,
        "pct_from_high":    float,   # negative = below high
        "in_add_zone":      bool,    # True if 8–12% below high
        "pattern_active":   bool,    # 1979 accumulation phase
        "reversal_risk":    bool,    # 1979 blow-off exit signal
        "status":           str,
        "analog_note":      str,
        "ok":               bool,
    }
    """
    from config import GOLD_TRACKER, THRESHOLDS
    try:
        hist = yf.Ticker("GLD").history(period="100d")
        if len(hist) < 62:
            return {"ok": False}

        latest  = float(hist["Close"].iloc[-1])

        ret_30d = round((latest / float(hist["Close"].iloc[-31])  - 1) * 100, 2) if len(hist) >= 31 else None
        ret_60d = round((latest / float(hist["Close"].iloc[-61])  - 1) * 100, 2) if len(hist) >= 61 else None
        ret_90d = round((latest / float(hist["Close"].iloc[-91])  - 1) * 100, 2) if len(hist) >= 91 else None

        # Recent high (20-day)
        recent_high   = float(hist["Close"].iloc[-20:].max())
        pct_from_high = round((latest - recent_high) / recent_high * 100, 2)

        # Add zone: 8–12% below recent high
        add_low  = -GOLD_TRACKER["add_on_pullback_pct"] - 4   # -12%
        add_high = -GOLD_TRACKER["add_on_pullback_pct"]        # -8%
        in_add_zone = add_low <= pct_from_high <= add_high

        # 1979 pattern signals
        pattern_active = ret_60d is not None and ret_60d >= GOLD_TRACKER["pattern_active_threshold_pct"]
        reversal_risk  = ret_60d is not None and ret_60d >= GOLD_TRACKER["reversal_risk_threshold_pct"]

        # Status from threshold config
        t = THRESHOLDS["gold_60d"]
        r = ret_60d or 0
        if   r >= t["critical"][0]: status = "critical"
        elif r >= t["warning"][0]:  status = "warning"
        elif r >= t["elevated"][0]: status = "elevated"
        else:                       status = "normal"

        # Analog note
        if reversal_risk:
            note = "REVERSAL RISK: Gold >40% in 60d. 1979 ended here — Volcker hiked, gold -40% in 8wks. Reduce IAU 40-50%."
        elif pattern_active:
            note = "1979 PATTERN ACTIVE: Gold >25% in 60d. Accumulation phase — add IAU on 8-12% pullbacks only."
        elif in_add_zone:
            note = f"IN ADD ZONE: Gold {pct_from_high:+.1f}% from recent high. Add IAU here per playbook."
        else:
            note = "Monitoring. Below 1979 pattern threshold."

        return {
            "ret_30d":       ret_30d,
            "ret_60d":       ret_60d,
            "ret_90d":       ret_90d,
            "recent_high":   round(recent_high, 2),
            "pct_from_high": pct_from_high,
            "in_add_zone":   in_add_zone,
            "pattern_active": pattern_active,
            "reversal_risk": reversal_risk,
            "status":        status,
            "analog_note":   note,
            "ok":            True,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── New: Japan 10yr yield ────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_japan_10y() -> dict:
    """
    Fetch Japan 10-year government bond yield from FRED.
    This closes the mechanism gap: JGB yields rising → BoJ forced to act
    → Treasury selling → US 10yr spikes.

    Combination fires when JP10Y > 1.0% AND USD/JPY > 148 simultaneously.

    Returns: {
        "jp10y":          float,   # current yield %
        "change_1d":      float,   # 1-day move in bps
        "status":         str,     # normal / elevated / warning / critical
        "boj_cap_pct":    float,   # how far above BoJ soft cap (1.0%)
        "mechanism_active": bool,  # JP10Y > 1.0% AND USDJPY > 148
        "ok":             bool,
    }
    """
    from config import THRESHOLDS, JAPAN_TRACKER
    try:
        series = fetch_fred_series(FRED_SERIES["jp10y"], days=30)
        if series.empty or len(series) < 2:
            return {"ok": False}

        current  = float(series.iloc[-1])
        previous = float(series.iloc[-2])
        chg_bps  = round((current - previous) * 100, 1)   # convert % to bps

        t = THRESHOLDS["jp10y"]
        if   current >= t["critical"][0]: status = "critical"
        elif current >= t["warning"][0]:  status = "warning"
        elif current >= t["elevated"][0]: status = "elevated"
        else:                             status = "normal"

        boj_cap_pct = round(current - JAPAN_TRACKER["boj_soft_cap_pct"], 3)

        return {
            "jp10y":          round(current, 3),
            "previous":       round(previous, 3),
            "change_bps":     chg_bps,
            "status":         status,
            "boj_cap_pct":    boj_cap_pct,
            "above_boj_cap":  current >= JAPAN_TRACKER["jp10y_warning_pct"],
            "ok":             True,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── New: Episode tracker ─────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_episode_score(conflict_day: int = 23) -> dict:
    """
    Score current trajectory against 5 historical oil shock episodes.
    Returns which episode 2026 most closely resembles and at what confidence.

    Scoring dimensions:
      1. Oil spike speed  (days to reach current % gain)
      2. S&P drawdown     (where on the drawdown curve are we?)
      3. Gold behavior    (flat like 1990 or parabolic like 1979?)

    Returns: {
        "scores":     { episode_id: float (0-1) },
        "best_match": str,   # episode key e.g. "1973"
        "confidence": float, # 0-1
        "label":      str,   # human readable
        "scenario_weight": str,  # "A" | "B" | "C"
        "note":       str,
        "ok":         bool,
    }
    """
    from config import HISTORICAL_EPISODES, EPISODE_SCORER
    try:
        # Fetch current readings
        prices = fetch_live_prices()

        oil_px  = get_current_value(prices, "oil",   "price")
        oil_ytd = get_current_value(prices, "oil",   "ytd_pct")
        sp_high = get_current_value(prices, "sp500", "pct_from_high")
        gold_tr = get_gold_tracker()

        if oil_px is None:
            return {"ok": False, "note": "Insufficient data"}

        # Current readings
        current_oil_spike   = oil_ytd or 68        # % gain since conflict onset
        current_sp_drawdown = sp_high or -6.7      # % from peak (negative)
        current_gold_60d    = gold_tr.get("ret_60d") or 12.0

        scores = {}
        for ep_id, ep in HISTORICAL_EPISODES.items():
            if ep_id == "2026":
                continue

            score = 0.0

            # Dimension 1: Oil spike speed
            # How close is current spike % to episode's peak at equivalent days?
            ep_oil_at_day = ep["oil_peak_pct"] * min(1.0, conflict_day / max(ep["days_to_oil_peak"], 1))
            oil_diff = abs(current_oil_spike - ep_oil_at_day)
            oil_score = max(0, 1 - oil_diff / 100)
            score += oil_score * EPISODE_SCORER["oil_speed_weight"]

            # Dimension 2: S&P drawdown trajectory
            ep_sp_at_day = ep["sp_drawdown_pct"] * min(1.0, conflict_day / (ep["duration_months"] * 21))
            sp_diff  = abs(current_sp_drawdown - ep_sp_at_day)
            sp_score = max(0, 1 - sp_diff / 30)
            score += sp_score * EPISODE_SCORER["sp_trajectory_weight"]

            # Dimension 3: Gold behavior
            ep_gold = ep.get("gold_pct_12mo") or 0
            ep_gold_at_day = ep_gold * min(1.0, conflict_day / 250)   # scale to ~1yr
            gold_diff  = abs(current_gold_60d - ep_gold_at_day)
            gold_score = max(0, 1 - gold_diff / 50)
            score += gold_score * EPISODE_SCORER["gold_behavior_weight"]

            scores[ep_id] = round(score, 3)

        if not scores:
            return {"ok": False}

        best_match  = max(scores, key=scores.get)
        confidence  = scores[best_match]
        ep_data     = HISTORICAL_EPISODES[best_match]
        sc_weight   = ep_data.get("scenario_weight", "B")

        if confidence < EPISODE_SCORER["min_confidence"]:
            note = f"No confident analog match yet (best: {best_match} at {confidence:.0%}). Too early — check again at day 30+."
        else:
            note = (
                f"Closest analog: {ep_data['label']} ({confidence:.0%} confidence). "
                f"Historical outcome: S&P {ep_data['sp_drawdown_pct']}% over {ep_data['duration_months']} months. "
                f"Weights toward Scenario {sc_weight}."
            )

        return {
            "scores":          scores,
            "best_match":      best_match,
            "confidence":      round(confidence, 3),
            "label":           ep_data["label"],
            "scenario_weight": sc_weight,
            "structural_match": ep_data.get("structural_match", False),
            "note":            note,
            "ok":              True,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── New: Action trigger evaluator ────────────────────────────────────────────

def evaluate_action_triggers(prices: dict, signal_states: dict) -> list:
    """
    Check all ACTION_TRIGGERS from config against current signal states.
    Returns list of triggers with current status: monitoring / watch / enter / active.

    signal_states expected keys:
      hyg_credit: dict from get_hyg_credit_stress()
      pe_basket:  dict from get_pe_basket()
      gold:       dict from get_gold_tracker()
      ma200:      dict from get_200day_ma()
      jp10y:      dict from get_japan_10y()
    """
    from config import ACTION_TRIGGERS
    results = []

    hyg    = signal_states.get("hyg_credit", {})
    pe     = signal_states.get("pe_basket", {})
    gold   = signal_states.get("gold", {})
    ma200  = signal_states.get("ma200", {})

    oil_px  = get_current_value(prices, "oil",  "price") or 0
    vix_val = get_current_value(prices, "vix",  "price") or 0
    qqq_pfh = get_current_value(prices, "qqq",  "pct_from_high") or 0
    ewy_pfh = get_current_value(prices, "ewy",  "pct_from_high") or 0
    xle_pfh = get_current_value(prices, "xle",  "pct_from_high") or 0
    gold_pfh = gold.get("pct_from_high", 0)

    for trigger in ACTION_TRIGGERS:
        tid    = trigger["id"]
        status = trigger.get("status", "monitoring")
        flags  = []   # conditions currently met
        total  = 0    # total conditions

        # ── HYG puts / PE short ───────────────────────────────────────────
        if tid == "hyg_puts_pe_short":
            total = 2
            hyg_ok = hyg.get("ok") and hyg.get("hyg_5d_ret", 0) <= -1.5
            pe_ok  = pe.get("ok")  and pe.get("spread", 0)       <= -5.0
            if hyg_ok: flags.append("HYG 5d ≤ −1.5%")
            if pe_ok:  flags.append("PE basket vs SPY ≤ −5%")
            if len(flags) == 2: status = "enter"
            elif len(flags) == 1: status = "watch"
            else: status = "monitoring"

        # ── NVDA / PLTR puts ──────────────────────────────────────────────
        elif tid == "nvda_pltr_puts_ai":
            total = 3
            ma_ok  = ma200.get("ok") and not ma200.get("above_200d", True) and ma200.get("streak_days", 0) >= 5
            oil_ok = oil_px >= 95
            qqq_ok = qqq_pfh <= -15.0
            if ma_ok:  flags.append("S&P ≥5 days below 200d MA")
            if oil_ok: flags.append(f"Oil ≥$95 (${oil_px:.0f})")
            if qqq_ok: flags.append(f"QQQ {qqq_pfh:.1f}% from peak")
            if len(flags) == 3: status = "enter"
            elif len(flags) >= 2: status = "watch"
            else: status = "monitoring"

        # ── IAU gold accumulate ───────────────────────────────────────────
        elif tid == "iau_gold_accumulate":
            total = 3
            pb_ok  = -12.0 <= gold_pfh <= -8.0
            oil_ok = oil_px >= 90
            rev_ok = not gold.get("reversal_risk", False)
            if pb_ok:  flags.append(f"Gold {gold_pfh:.1f}% from high (add zone)")
            if oil_ok: flags.append(f"Oil ≥$90 (${oil_px:.0f})")
            if rev_ok: flags.append("No reversal risk")
            if len(flags) == 3: status = "enter"
            elif len(flags) == 2: status = "watch"
            else: status = "active"   # already holding, just not in add zone

        # ── XLE hold / divergence ─────────────────────────────────────────
        elif tid == "xle_hold_divergence":
            # Status is driven by divergence rule firing
            div = signal_states.get("xle_divergence", {})
            if div.get("diverging"):
                status = "exit"
                flags  = ["XLE/oil divergence detected — sell signal active"]
            elif xle_pfh <= -8.0 and oil_px >= 90:
                status = "enter"   # add zone
                flags  = [f"XLE {xle_pfh:.1f}% from high", f"Oil ${oil_px:.0f}"]
            else:
                status = "active"   # hold, no add trigger yet

        # ── EWY peace trade ───────────────────────────────────────────────
        elif tid == "ewy_peace_trade":
            total = 2
            vix_ok = vix_val >= 35
            ewy_ok = ewy_pfh <= -15.0
            if vix_ok: flags.append(f"VIX {vix_val:.1f} ≥ 35")
            if ewy_ok: flags.append(f"EWY {ewy_pfh:.1f}% from pre-conflict high")
            if len(flags) == 2: status = "enter"
            elif len(flags) == 1: status = "watch"
            else: status = "monitoring"

        # ── QQQ capitulation buy ──────────────────────────────────────────
        elif tid == "qqq_capitulation_buy":
            total = 3
            vix_ok = vix_val >= 40
            qqq_ok = qqq_pfh <= -20.0
            # Oil stabilizing = no longer in 6-session rising streak
            mom = signal_states.get("momentum", {})
            oil_stable = mom.get("oil") != "rising"
            if vix_ok:      flags.append(f"VIX {vix_val:.1f} ≥ 40 (capitulation)")
            if qqq_ok:      flags.append(f"QQQ {qqq_pfh:.1f}% from peak")
            if oil_stable:  flags.append("Oil momentum not rising")
            if len(flags) == 3: status = "enter"
            elif len(flags) >= 2: status = "watch"
            else: status = "monitoring"

        results.append({
            **trigger,
            "status":           status,
            "conditions_met":   flags,
            "conditions_total": total,
        })

    return results


# ─── Private helpers ──────────────────────────────────────────────────────────

def _empty_200d(error: str = "fetch failed") -> dict:
    return {
        "ma_200": None, "current_price": None, "above_200d": None,
        "streak_days": None, "pct_from_ma": None, "ok": False, "error": error,
    }


def _empty_price(ticker: str, error: str = "fetch failed") -> dict:
    return {
        "ticker":        ticker,
        "price":         None,
        "change_pct":    None,
        "change_abs":    None,
        "ytd_pct":       None,
        "high_52w":      None,
        "pct_from_high": None,
        "timestamp":     None,
        "ok":            False,
        "error":         error,
    }


def format_price(value, prefix="$", decimals=2) -> str:
    """Format a price for display. Returns '—' if None."""
    if value is None:
        return "—"
    return f"{prefix}{value:,.{decimals}f}"


def format_change(value, suffix="%", show_plus=True) -> str:
    """Format a change value with sign. Returns '—' if None."""
    if value is None:
        return "—"
    sign = "+" if value > 0 and show_plus else ""
    return f"{sign}{value:.2f}{suffix}"


def format_pct(value) -> str:
    return format_change(value, suffix="%")
