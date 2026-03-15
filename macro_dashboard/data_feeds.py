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


# ─── Private helpers ───────────────────────────────────────────────────────────

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
