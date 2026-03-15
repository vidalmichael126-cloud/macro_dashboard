"""
config.py — Single source of truth for all thresholds, tickers, and rules.
Change numbers here; everything else updates automatically.
"""

# ─── Data sources ─────────────────────────────────────────────────────────────

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="

FRED_SERIES = {
    "yield_10yr":    "DGS10",       # 10-year Treasury yield
    "yield_2yr":     "DGS2",        # 2-year Treasury yield
    "yield_curve":   "T10Y2Y",      # 2s10s spread (10yr minus 2yr)
    "vix_fred":      "VIXCLS",      # VIX (daily, 1-day lag vs live)
    "oil_fred":      "DCOILWTICO",  # WTI crude (daily)
    "dxy":           "DTWEXBGS",    # Dollar index (broad)
    "cpi":           "CPIAUCSL",    # CPI (monthly)
    "unemployment":  "UNRATE",      # Unemployment rate (monthly)
}

YAHOO_TICKERS = {
    "oil":       "CL=F",      # WTI crude futures
    "vix":       "^VIX",      # CBOE VIX
    "sp500":     "^GSPC",     # S&P 500
    "nasdaq":    "^IXIC",     # Nasdaq Composite
    "yield_10":  "^TNX",      # 10-year Treasury yield
    "usdjpy":    "JPY=X",     # USD/JPY
    "gold":      "GLD",       # Gold ETF
    "xle":       "XLE",       # Energy sector ETF
    "hyg":       "HYG",       # High-yield (junk) bonds
    "ewy":       "EWY",       # South Korea ETF (KOSPI proxy)
    "ewj":       "EWJ",       # Japan ETF (Nikkei proxy)
    "btc":       "BTC-USD",   # Bitcoin
    "qqq":       "QQQ",       # Nasdaq 100 ETF
    "tbf":       "TBF",       # Short long-term bonds ETF
    "sh":        "SH",        # Inverse S&P 500 ETF
    "spy":       "SPY",       # S&P 500 ETF
}

# ─── Signal thresholds ────────────────────────────────────────────────────────
# Each signal has: value zones and what they mean.
# Status: "normal" | "elevated" | "warning" | "critical"

THRESHOLDS = {
    "oil": {
        "normal":   (0,    90),    # Below $90 — conflict easing or resolved
        "elevated": (90,   120),   # $90–120 — Scenario B territory
        "warning":  (120,  150),   # $120–150 — Oxford Economics recession threshold
        "critical": (150,  999),   # $150+ — Scenario C, full escalation
        "unit": "$/barrel",
        "description": "WTI crude oil price",
    },
    "vix": {
        "normal":   (0,    20),    # Calm market
        "elevated": (20,   30),    # Stress, heightened uncertainty
        "warning":  (30,   40),    # Fear — institutional de-risking
        "critical": (40,   999),   # Capitulation — historically a buy signal
        "unit": "index",
        "description": "CBOE Volatility Index (fear gauge)",
    },
    "yield_10": {
        "normal":   (0,    4.5),   # Below 4.5% — manageable
        "elevated": (4.5,  5.0),   # 4.5–5.0% — stress on mortgages, PE
        "warning":  (5.0,  5.5),   # 5.0–5.5% — debt spiral accelerating
        "critical": (5.5,  99),    # 5.5%+ — fiscal crisis territory
        "unit": "%",
        "description": "10-year US Treasury yield",
    },
    "usdjpy": {
        "normal":   (0,    148),   # Below 148 — yen stable
        "elevated": (148,  152),   # 148–152 — weakening, watch
        "warning":  (152,  155),   # 152–155 — intervention risk rising
        "critical": (155,  999),   # 155+ — intervention likely, carry unwind risk
        "unit": "¥/$",
        "description": "USD/JPY exchange rate",
        "note": "Higher = weaker yen. Watch for SUDDEN DROP — that signals carry trade unwind.",
    },
    "yield_curve": {
        "normal":   (-0.5,  2.0),  # Positive or mildly inverted
        "elevated": (-1.0, -0.5),  # Inverted — recession signal
        "warning":  (-1.5, -1.0),  # Deeply inverted — strong recession signal
        "critical": (-99,  -1.5),  # Very deep inversion
        "unit": "%",
        "description": "2s10s yield curve spread (10yr minus 2yr)",
        "note": "Negative = inverted = recession historically follows within 12–18 months.",
    },
}

# ─── Signal combination rules ─────────────────────────────────────────────────
# When multiple signals fire together, they form a named pattern.
# Each rule checks a dict of {signal_name: minimum_status_level}.
# Status levels: 0=normal, 1=elevated, 2=warning, 3=critical

STATUS_LEVELS = {"normal": 0, "elevated": 1, "warning": 2, "critical": 3}

COMBINATION_RULES = [
    {
        "name": "Sell America",
        "description": "Capital leaving the US entirely — not just rotating within it.",
        "action": "Add TBF (short bonds). Increase gold. Consider SH hedge on S&P.",
        "severity": "critical",
        "conditions": {
            "oil": "elevated",        # Oil rising
            "yield_10": "elevated",   # Yields rising (bonds being sold)
            "vix": "elevated",        # Fear elevated
        },
        "additional_check": "dollar_falling",  # Dollar must also be falling
    },
    {
        "name": "XLE-Oil divergence",
        "description": "Energy stocks falling while oil still high — market pricing conflict resolution 3–6 weeks early.",
        "action": "Take profits on XLE. Rotate into quality beaten-down equities (QQQ, EWY).",
        "severity": "warning",
        "conditions": {},  # Evaluated separately via price comparison logic
        "special": "xle_oil_divergence",
    },
    {
        "name": "VIX capitulation",
        "description": "Peak fear. Historically marks S&P bottom within 2–6 weeks.",
        "action": "Aggressive buy signal for long-term. Increase 401k contribution rate if possible. Consider tactical QQQ.",
        "severity": "opportunity",
        "conditions": {
            "vix": "critical",        # VIX above 40
        },
    },
    {
        "name": "Carry trade unwind risk",
        "description": "Yen approaching intervention threshold. If Bank of Japan acts, yen strengthens rapidly, carry trades unwind, US markets sell off.",
        "action": "Reduce leveraged positions NOW. Watch for sudden USD/JPY drop below 148 as the actual trigger.",
        "severity": "critical",
        "conditions": {
            "usdjpy": "critical",     # USD/JPY above 155
        },
    },
    {
        "name": "Stagflation confirmed",
        "description": "Oil shock driving inflation while growth stalls. Fed paralyzed.",
        "action": "Max gold allocation. Hold energy. Short long-duration bonds (TBF). Avoid tech.",
        "severity": "warning",
        "conditions": {
            "oil": "warning",         # Oil above $120
            "yield_10": "elevated",   # Yields rising
        },
    },
]

# ─── Scenario definitions ─────────────────────────────────────────────────────

SCENARIOS = {
    "A": {
        "name": "Scenario A — Peace deal",
        "description": "Conflict resolves. Hormuz reopens. Risk-on returns.",
        "oil_range": "$70–90",
        "probability_default": 32,
        "color_bg": "#EAF3DE",
        "color_border": "#639922",
        "color_text": "#27500A",
        "color_subtext": "#3B6D11",
        "actions": [
            "Sell XLE / energy positions",
            "Rotate into QQQ and beaten-down quality tech",
            "Sell SH and inverse ETF positions immediately",
            "Buy EWY — Korean market recovers fastest",
        ],
    },
    "B": {
        "name": "Scenario B — Prolonged conflict",
        "description": "Conflict drags 4–8 weeks. Stagflation building. Fed paralyzed.",
        "oil_range": "$120–150",
        "probability_default": 47,
        "color_bg": "#FAEEDA",
        "color_border": "#EF9F27",
        "color_text": "#412402",
        "color_subtext": "#854F0B",
        "actions": [
            "Hold XLE and energy — do not add near highs",
            "Add GLD on pullbacks (8–12% from high)",
            "Hold TBF — yields will keep rising",
            "Keep 401k contributions steady — VIX not at capitulation yet",
        ],
    },
    "C": {
        "name": "Scenario C — Full escalation",
        "description": "Sustained Hormuz closure. $150+ oil. Recession confirmed.",
        "oil_range": "$150–200",
        "probability_default": 21,
        "color_bg": "#FCEBEB",
        "color_border": "#E24B4A",
        "color_text": "#501313",
        "color_subtext": "#A32D2D",
        "actions": [
            "Maximum defensive posture — raise cash to 20–30%",
            "Max gold allocation",
            "SH hedge on S&P 500",
            "Exit long-duration bonds entirely",
            "Wait for VIX 40+ spike as the eventual buy signal",
        ],
    },
}

# ─── Scenario scoring logic ───────────────────────────────────────────────────
# Adjusts default probabilities based on current signal states.
# Each rule adds/subtracts probability points from each scenario.

SCENARIO_SCORING_RULES = [
    # Oil level drives the primary split
    {"condition": "oil_above_150", "A": -20, "B": -10, "C": +30},
    {"condition": "oil_above_120", "A": -15, "B": +10, "C": +5},
    {"condition": "oil_below_90",  "A": +20, "B": -15, "C": -5},
    # VIX tells you about resolution vs escalation
    {"condition": "vix_above_40",  "A": +5,  "B": -5,  "C":  0},
    {"condition": "vix_below_20",  "A": +10, "B": -5,  "C": -5},
    # XLE divergence is an early peace signal
    {"condition": "xle_diverging", "A": +15, "B": -10, "C": -5},
    # Yield curve stress confirms macro damage
    {"condition": "yield_above_5", "A": -5,  "B": +5,  "C":  0},
    # Carry trade stress = systemic risk = escalation
    {"condition": "usdjpy_critical","A": -5, "B":  0,  "C": +5},
]

# ─── Display settings ─────────────────────────────────────────────────────────

REFRESH_INTERVALS = {
    "tier1_minutes": 15,    # Oil, VIX, USD/JPY, XLE during market hours
    "tier2_hours":   24,    # Daily close data
    "cache_hours":   1,     # How long to cache yfinance data
}

SPARKLINE_DAYS = 20         # Days of history shown in sparklines

APP_TITLE = "Macro Signal Dashboard"
APP_ICON = "📡"
