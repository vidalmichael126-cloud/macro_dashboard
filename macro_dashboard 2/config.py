"""
config.py — Single source of truth for all thresholds, tickers, rules,
structural priors, action triggers, and ledger schema.

Change numbers here; everything else updates automatically.
Last structural update: March 2026 — Burry engine v1
"""

# ─── Data sources ─────────────────────────────────────────────────────────────

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="

FRED_SERIES = {
    "yield_10yr":    "DGS10",
    "yield_2yr":     "DGS2",
    "yield_curve":   "T10Y2Y",
    "vix_fred":      "VIXCLS",
    "oil_fred":      "DCOILWTICO",
    "dxy":           "DTWEXBGS",
    "cpi":           "CPIAUCSL",
    "unemployment":  "UNRATE",
    "jp10y":         "IRLTLT01JPM156N",
}

YAHOO_TICKERS = {
    # Core macro
    "oil":    "CL=F",
    "vix":    "^VIX",
    "sp500":  "^GSPC",
    "nasdaq": "^IXIC",
    "yield_10": "^TNX",
    "usdjpy": "JPY=X",
    "gold":   "GLD",
    "xle":    "XLE",
    "hyg":    "HYG",
    "ewy":    "EWY",
    "ewj":    "EWJ",
    "qqq":    "QQQ",
    "tbf":    "TBF",
    "spy":    "SPY",
    "iwm":    "IWM",
    "fez":    "FEZ",
    "ita":    "ITA",
    "ovx":    "^OVX",
    "sh":     "SH",
    "btc":    "BTC-USD",
    # PE basket
    "bx":    "BX",
    "kkr":   "KKR",
    "apo":   "APO",
    "ares":  "ARES",
    "owl":   "OWL",
    # Gold / energy
    "gdx":   "GDX",
    "iau":   "IAU",
    "sgov":  "SGOV",
    # AI thesis
    "nvda":  "NVDA",
    "pltr":  "PLTR",
}

# ─── Structural priors (Dalio framework) ──────────────────────────────────────

STRUCTURAL_PRIORS = {
    "debt_gdp_pct":      102,
    "scenario_c_bias":   +5,
    "scenario_a_bias":   -5,
    "scenario_b_bias":    0,
    "petrodollar_strain": True,
    "fed_room_to_hike":   False,
    "basis_year":         2026,
    "next_review":        "Q3 2026",
    "rationale": (
        "At 102% debt/GDP the Fed cannot execute a Volcker-style rate shock. "
        "1973 analog: 35% debt/GDP. 1990: 55%. The structural constraint permanently "
        "reduces Scenario A probability and raises Scenario C."
    ),
}

# ─── Signal thresholds ────────────────────────────────────────────────────────

STATUS_LEVELS = {"normal": 0, "elevated": 1, "warning": 2, "critical": 3}

THRESHOLDS = {
    "oil": {
        "normal":   (0,    90),
        "elevated": (90,   120),
        "warning":  (120,  150),
        "critical": (150,  999),
        "unit": "$/barrel",
        "description": "WTI crude oil price",
        "note": "Oxford Economics: $140 = recession onset threshold.",
    },
    "vix": {
        "normal":   (0,   20),
        "elevated": (20,  30),
        "warning":  (30,  40),
        "critical": (40,  999),
        "unit": "index",
        "description": "CBOE Volatility Index",
        "note": "VIX >40 historically marks S&P bottom +/-6 weeks. Do not buy before.",
    },
    "yield_10": {
        "normal":   (0,   4.5),
        "elevated": (4.5, 5.0),
        "warning":  (5.0, 5.5),
        "critical": (5.5, 99),
        "unit": "%",
        "description": "10-year US Treasury yield",
        "note": "5-day consecutive rise is the early warning signal.",
    },
    "usdjpy": {
        "normal":   (0,   148),
        "elevated": (148, 152),
        "warning":  (152, 155),
        "critical": (155, 999),
        "unit": "yen/$",
        "description": "USD/JPY exchange rate",
        "note": "Watch for SUDDEN DROP below 148 — that signals carry trade unwind.",
    },
    "yield_curve": {
        "normal":   (-0.5,  2.0),
        "elevated": (-1.0, -0.5),
        "warning":  (-1.5, -1.0),
        "critical": (-99,  -1.5),
        "unit": "%",
        "description": "2s10s yield curve spread",
        "note": "Negative = inverted = recession historically follows within 12-18 months.",
    },
    "hyg_5d": {
        "normal":   (-0.5,  99),
        "elevated": (-1.5, -0.5),
        "warning":  (-3.0, -1.5),
        "critical": (-99,  -3.0),
        "unit": "%",
        "description": "HYG 5-day return — high-yield credit health",
        "note": "PE firms hold $2.5T floating-rate debt. HYG falling = their cost of capital rising.",
    },
    "pe_vs_spy_10d": {
        "normal":   (-2.0,  99),
        "elevated": (-5.0, -2.0),
        "warning":  (-8.0, -5.0),
        "critical": (-99,  -8.0),
        "unit": "%",
        "description": "PE basket vs SPY 10-day return spread",
        "note": "When PE lags SPY >5% AND HYG falling: Burry PE short entry signal.",
    },
    "gold_60d": {
        "normal":   (0,   10),
        "elevated": (10,  25),
        "warning":  (25,  40),
        "critical": (40,  999),
        "unit": "%",
        "description": "Gold 60-day % change — 1979 parabolic tracker",
        "note": "1979: gold +490% then -40% in 8 weeks on Volcker. At >40% in 60d: reduce IAU.",
    },
    "jp10y": {
        "normal":   (0,   0.8),
        "elevated": (0.8, 1.0),
        "warning":  (1.0, 1.2),
        "critical": (1.2, 99),
        "unit": "%",
        "description": "Japan 10-year government bond yield",
        "note": "Japan holds $1.1T US Treasuries. JP10Y >1.0% + USDJPY >148 = Treasury selloff mechanism.",
    },
}

# ─── PE basket ────────────────────────────────────────────────────────────────

PE_BASKET = {
    "tickers":           ["BX", "KKR", "APO", "ARES", "OWL"],
    "weights":           [0.20, 0.20, 0.20, 0.20, 0.20],
    "lookback_days":     10,
    "lag_threshold_pct": -5.0,
    "description":       "Blackstone, KKR, Apollo, Ares, Blue Owl — equal-weight PE stress index",
    "thesis": (
        "PE firms hold ~$2.5T in floating-rate leveraged loans. "
        "Rates hold elevated = interest coverage collapses = distributions freeze = LP selling."
    ),
}

# ─── Gold tracker ─────────────────────────────────────────────────────────────

GOLD_TRACKER = {
    "pattern_active_threshold_pct":  25,
    "reversal_risk_threshold_pct":   40,
    "lookback_days_medium":          60,
    "lookback_days_long":            90,
    "add_on_pullback_pct":           8,
    "target_allocation_pct":         10,
    "analog_note": (
        "1979: Gold $226 to $843 (+275%) in 12 months, then -40% in 8 weeks on Volcker. "
        "Current: $4,660 as of March 2026. Watch for policy shock as exit trigger."
    ),
}

# ─── Japan tracker ────────────────────────────────────────────────────────────

JAPAN_TRACKER = {
    "boj_soft_cap_pct":          1.0,
    "jp10y_warning_pct":         1.0,
    "jp10y_critical_pct":        1.2,
    "usdjpy_co_trigger":         148,
    "japan_treasury_holdings_bn": 1100,
    "mechanism": (
        "JGB yields rise → BoJ forced to defend cap → sells US Treasuries → "
        "10yr yield spikes → dollar falls → Sell America confirmed."
    ),
}

# ─── Historical episode curves ────────────────────────────────────────────────

HISTORICAL_EPISODES = {
    "1973": {
        "label":             "1973 — Yom Kippur / OPEC embargo",
        "oil_peak_pct":       300,
        "sp_drawdown_pct":   -48,
        "gold_pct_12mo":     +72,
        "duration_months":    21,
        "days_to_oil_peak":   150,
        "structural_match":   True,
        "scenario_weight":    "C",
        "color":              "#E24B4A",
    },
    "1979": {
        "label":             "1979 — Iranian Revolution",
        "oil_peak_pct":       160,
        "sp_drawdown_pct":   -17,
        "gold_pct_12mo":     +490,
        "duration_months":    18,
        "days_to_oil_peak":   365,
        "structural_match":   False,
        "scenario_weight":    "B",
        "color":              "#D85A30",
    },
    "1990": {
        "label":             "1990 — Gulf War / Kuwait",
        "oil_peak_pct":      +75,
        "sp_drawdown_pct":   -20,
        "gold_pct_12mo":     +12,
        "duration_months":    9,
        "days_to_oil_peak":   60,
        "structural_match":   False,
        "scenario_weight":    "A",
        "color":              "#639922",
    },
    "2008": {
        "label":             "2008 — Financial crisis",
        "oil_peak_pct":       147,
        "sp_drawdown_pct":   -57,
        "gold_pct_12mo":     +5,
        "duration_months":    17,
        "days_to_oil_peak":   200,
        "structural_match":   False,
        "scenario_weight":    "C",
        "color":              "#534AB7",
    },
    "2022": {
        "label":             "2022 — Russia / Ukraine",
        "oil_peak_pct":      +68,
        "sp_drawdown_pct":   -25,
        "gold_pct_12mo":     -3,
        "duration_months":    12,
        "days_to_oil_peak":   14,
        "structural_match":   False,
        "scenario_weight":    "B",
        "color":              "#1D9E75",
    },
}

EPISODE_SCORER = {
    "oil_speed_weight":      0.35,
    "sp_trajectory_weight":  0.40,
    "gold_behavior_weight":  0.25,
    "min_confidence":        0.40,
}

# ─── Combination rules ────────────────────────────────────────────────────────

COMBINATION_RULES = [
    {
        "name": "Sell America",
        "description": "Capital leaving the US entirely. Yields rising AND dollar falling = foreign holders exiting both bonds and currency.",
        "action": "Add TBF. Increase gold. Consider SH hedge on S&P.",
        "severity": "critical",
        "conditions": {
            "oil":      "elevated",
            "yield_10": "elevated",
            "vix":      "elevated",
        },
        "additional_check": "dollar_falling",
        "connected_signals": ["oil", "yield_10", "vix", "dxy", "usdjpy"],
    },
    {
        "name": "XLE/oil divergence",
        "description": "Energy stocks falling while oil holds above $90 — market pricing peace 3-6 weeks early.",
        "action": "Take profits on XLE immediately. Rotate into EWY.",
        "severity": "warning",
        "conditions": {},
        "special": "xle_oil_divergence",
        "connected_signals": ["xle", "oil"],
    },
    {
        "name": "VIX capitulation",
        "description": "Peak fear. Historically marks S&P bottom within 2-6 weeks.",
        "action": "Aggressive buy. Increase 401k. Add QQQ and EWY. This is what you waited for.",
        "severity": "opportunity",
        "conditions": {"vix": "critical"},
        "connected_signals": ["vix", "sp500"],
    },
    {
        "name": "Carry trade unwind",
        "description": "Yen at critical threshold. BoJ intervention imminent. Forced US asset selling follows.",
        "action": "Reduce leveraged positions NOW. Watch for sudden USD/JPY drop below 148.",
        "severity": "critical",
        "conditions": {"usdjpy": "critical"},
        "connected_signals": ["usdjpy", "ewj", "yield_10", "jp10y"],
    },
    {
        "name": "Stagflation building",
        "description": "Oil shock driving inflation while growth stalls. Fed paralyzed at 102% debt/GDP.",
        "action": "Max gold (IAU). Hold XLE. Short long-duration bonds (TBF). Avoid tech.",
        "severity": "warning",
        "conditions": {
            "oil":      "warning",
            "yield_10": "elevated",
        },
        "connected_signals": ["oil", "yield_10", "vix", "gold"],
    },
    {
        "name": "200-day MA break",
        "description": "S&P below 200-day MA. Institutional algorithms in sell mode. In 1973 this preceded worst losses by 6 months.",
        "action": "Do not buy the dip. Wait for VIX >35 OR 200-day reclaim with volume.",
        "severity": "critical",
        "conditions": {},
        "special": "sp500_200day_break",
        "connected_signals": ["sp500", "vix", "iwm"],
    },
    {
        "name": "Recession pricing",
        "description": "Small caps underperforming large caps — credit stress and demand destruction signal.",
        "action": "Reduce cyclicals. Shift toward SGOV and TBF. Watch IWM vs SPY spread.",
        "severity": "warning",
        "conditions": {},
        "special": "recession_regime",
        "connected_signals": ["iwm", "spy", "hyg", "yield_curve"],
    },
    {
        "name": "PE credit stress — Burry signal",
        "description": "Two independent streams confirm PE debt burden simultaneously: HYG credit spreads widening AND PE basket underperforming SPY. This is the HYG put entry signal.",
        "action": "Enter HYG puts in Roth IRA. Strike 5-8% OTM, expiry 6-9 months. Size: 8-10% of Roth IRA.",
        "severity": "critical",
        "conditions": {
            "hyg_5d":        "warning",
            "pe_vs_spy_10d": "warning",
        },
        "connected_signals": ["hyg", "bx", "kkr", "apo", "ares", "owl", "yield_10"],
    },
    {
        "name": "Gold 1979 pattern active",
        "description": "Gold accelerating parabolically — tracking 1979 Iranian Revolution pattern. Accumulate phase.",
        "action": "Hold and add IAU on 8-12% pullbacks. Consider GDX calls. Do NOT chase.",
        "severity": "warning",
        "conditions": {"gold_60d": "warning"},
        "connected_signals": ["gold", "oil", "dxy", "yield_10"],
    },
    {
        "name": "Gold 1979 reversal risk",
        "description": "Gold in parabolic blow-off phase — where 1979 gold was just before Volcker caused a 40% collapse in 8 weeks.",
        "action": "Reduce IAU by 40-50%. Move proceeds to SGOV. This is your exit signal.",
        "severity": "critical",
        "conditions": {"gold_60d": "critical"},
        "connected_signals": ["gold", "yield_10", "vix"],
    },
    {
        "name": "Japan Treasury pressure",
        "description": "JGB yields approaching BoJ cap while yen weakening. Mechanism for forced US Treasury selling active.",
        "action": "Sell America confirmation. Add TBF. Reduce long-duration exposure.",
        "severity": "critical",
        "conditions": {
            "jp10y":  "warning",
            "usdjpy": "elevated",
        },
        "connected_signals": ["jp10y", "usdjpy", "yield_10", "ewj"],
    },
]

# ─── Scenario definitions ─────────────────────────────────────────────────────

SCENARIOS = {
    "A": {
        "name": "Scenario A — Peace deal",
        "description": "Conflict resolves. Hormuz reopens. Risk-on returns.",
        "oil_range": "$70–90",
        "probability_default": 32 + STRUCTURAL_PRIORS["scenario_a_bias"],
        "color_bg": "#EAF3DE",
        "color_border": "#639922",
        "color_text": "#27500A",
        "color_subtext": "#3B6D11",
        "historical_analog": "1990 Gulf War — 9-month spike, fast resolution, -20% S&P then full recovery",
        "actions": [
            "Sell XLE immediately on peace signal",
            "Rotate into QQQ and beaten-down quality tech",
            "Buy EWY — Korea recovers fastest on Hormuz reopening",
            "Exit TBF — yields fall as inflation fear eases",
        ],
    },
    "B": {
        "name": "Scenario B — Prolonged conflict",
        "description": "Conflict drags 4–8 weeks. Stagflation building. Fed paralyzed.",
        "oil_range": "$100–150",
        "probability_default": 47 + STRUCTURAL_PRIORS["scenario_b_bias"],
        "color_bg": "#FAEEDA",
        "color_border": "#EF9F27",
        "color_text": "#412402",
        "color_subtext": "#854F0B",
        "historical_analog": "1973 Yom Kippur — sustained shock, stagflation, -48% S&P over 21 months",
        "actions": [
            "Hold XLE — do not add near highs",
            "Add IAU on 8-12% pullbacks from recent high",
            "Hold TBF — yields will keep rising",
            "Keep 401k contributions steady — VIX not at capitulation yet",
            "Monitor HYG puts entry trigger (PE credit stress rule)",
        ],
    },
    "C": {
        "name": "Scenario C — Full escalation",
        "description": "Sustained Hormuz closure. $150+ oil. Recession confirmed.",
        "oil_range": "$150–200",
        "probability_default": 21 + STRUCTURAL_PRIORS["scenario_c_bias"],
        "color_bg": "#FCEBEB",
        "color_border": "#E24B4A",
        "color_text": "#501313",
        "color_subtext": "#A32D2D",
        "historical_analog": "1973 + 1979 combined — reserve currency stress, decade-long recovery",
        "actions": [
            "Maximum defensive posture — raise cash to 20-30%",
            "Max gold allocation (watch 1979 reversal rule)",
            "Enter HYG puts if PE credit stress rule fires",
            "Exit long-duration bonds entirely",
            "Wait for VIX 40+ capitulation as eventual buy signal",
        ],
    },
}

# ─── Scenario scoring rules ───────────────────────────────────────────────────

SCENARIO_SCORING_RULES = [
    {"condition": "oil_above_150",       "A": -20, "B": -10, "C": +30},
    {"condition": "oil_above_120",       "A": -15, "B": +10, "C": +5},
    {"condition": "oil_below_90",        "A": +20, "B": -15, "C": -5},
    {"condition": "vix_above_40",        "A": +5,  "B": -5,  "C":  0},
    {"condition": "vix_below_20",        "A": +10, "B": -5,  "C": -5},
    {"condition": "xle_diverging",       "A": +15, "B": -10, "C": -5},
    {"condition": "yield_above_5",       "A": -5,  "B": +5,  "C":  0},
    {"condition": "usdjpy_critical",     "A": -5,  "B":  0,  "C": +5},
    {"condition": "japan_pressure",      "A": -8,  "B":  0,  "C": +8},
    {"condition": "sp500_below_200d",    "A": -10, "B": +5,  "C": +5},
    {"condition": "recession_confirmed", "A": -5,  "B": -5,  "C": +10},
    {"condition": "pe_stress_confirmed", "A": -5,  "B":  0,  "C": +10},
    {"condition": "hyg_stress",          "A": -3,  "B": +3,  "C": +5},
    {"condition": "gold_1979_active",    "A": -5,  "B": +5,  "C": +5},
    {"condition": "analog_1973",         "A": -10, "B":  0,  "C": +10},
    {"condition": "analog_1990",         "A": +10, "B":  0,  "C": -10},
]

# ─── Action triggers ──────────────────────────────────────────────────────────

ACTION_TRIGGERS = [
    {
        "id":      "hyg_puts_pe_short",
        "name":    "HYG puts — PE debt burden",
        "thesis":  (
            "PE firms hold ~$2.5T floating-rate leveraged loans. "
            "Rates hold elevated → interest coverage collapses → distributions freeze → LP selling. "
            "HYG is the CDS equivalent — Burry structure: defined premium, asymmetric upside."
        ),
        "instrument": "HYG puts",
        "strike":     "5–8% OTM",
        "expiry":     "6–9 months",
        "account":    "Roth IRA",
        "size":       "8–10% of Roth IRA (premium only)",
        "entry_conditions": [
            "hyg_5d <= -1.5%",
            "pe_vs_spy_10d <= -5.0%",
        ],
        "entry_logic": "AND — both required simultaneously",
        "exit_profit":  "HYG drops to strike — roll down or take gains",
        "exit_stop":    "Fed signals rate cut OR HYG recovers for 3 consecutive days",
        "status":       "monitoring",
        "tickers":      ["HYG", "BX", "KKR", "APO", "ARES", "OWL"],
    },
    {
        "id":      "nvda_pltr_puts_ai",
        "name":    "NVDA / PLTR puts — AI capex compression",
        "thesis":  (
            "Data centers consume 2-3% of US electricity. Oil >$100 raises energy costs. "
            "NVDA ~30x sales, PLTR ~60x revenue — maximum rate sensitivity. "
            "Burry's current short. Lottery structure — deep OTM, small premium only."
        ),
        "instrument": "NVDA puts + PLTR puts",
        "strike":     "15–25% OTM",
        "expiry":     "6–9 months",
        "account":    "Roth IRA",
        "size":       "<2% of Roth IRA total (premium only)",
        "entry_conditions": [
            "sp500_below_200d >= 5 days",
            "oil >= 95",
            "qqq_from_peak <= -15%",
        ],
        "entry_logic": "AND",
        "exit_profit":  "50-75% gain on premium OR earnings miss event",
        "exit_stop":    "Oil drops below $85 OR Fed pivot to cuts",
        "status":       "watch",
        "tickers":      ["NVDA", "PLTR", "QQQ"],
    },
    {
        "id":      "iau_gold_accumulate",
        "name":    "IAU — gold accumulation on pullbacks",
        "thesis":  (
            "Gold tracking 1979 parabolic. Accumulation phase. "
            "Add on 8-12% pullbacks. Model fires 1979 reversal warning at >40% in 60 days — that is the exit."
        ),
        "instrument": "IAU",
        "strike":     "N/A",
        "expiry":     "N/A — hold until reversal signal",
        "account":    "Taxable brokerage",
        "size":       "Target 10% of taxable portfolio",
        "entry_conditions": [
            "gold_pullback_from_high >= 8%",
            "oil >= 90",
            "gold_1979_reversal_risk == False",
        ],
        "entry_logic": "AND",
        "exit_profit":  "Gold 1979 reversal risk rule fires — reduce 40-50%",
        "exit_stop":    "Peace deal + oil below $85 + gold reversal rule",
        "status":       "active",
        "tickers":      ["IAU", "GLD", "GDX"],
    },
    {
        "id":      "xle_hold_divergence",
        "name":    "XLE — hold, watch for divergence exit",
        "thesis":  (
            "XLE tracks oil but leads peace resolution by 3-6 weeks. "
            "Hold while oil above $90 and no divergence. XLE falling while oil holds = exit immediately."
        ),
        "instrument": "XLE",
        "strike":     "N/A",
        "expiry":     "N/A",
        "account":    "Taxable brokerage",
        "size":       "10% of taxable (current allocation)",
        "entry_conditions": [
            "xle_pullback_from_high >= 8%",
            "oil >= 90",
        ],
        "entry_logic": "AND — only add on dips",
        "exit_profit":  "XLE/oil divergence rule fires — sell immediately",
        "exit_stop":    "Oil drops below $85",
        "status":       "active",
        "tickers":      ["XLE", "HAL", "SLB"],
    },
    {
        "id":      "ewy_peace_trade",
        "name":    "EWY — Korea peace resolution bet",
        "thesis":  (
            "Korea prices peace fastest. Wait for VIX >35 and EWY down >15%. "
            "That is the washout entry — before peace becomes consensus."
        ),
        "instrument": "EWY",
        "strike":     "N/A",
        "expiry":     "N/A",
        "account":    "Taxable brokerage",
        "size":       "5% of taxable",
        "entry_conditions": [
            "vix >= 35",
            "ewy_from_pre_conflict_high <= -15%",
        ],
        "entry_logic": "AND",
        "exit_profit":  "+20% from entry OR peace confirmed",
        "exit_stop":    "Oil spikes above $130 — escalation not resolution",
        "status":       "monitoring",
        "tickers":      ["EWY"],
    },
    {
        "id":      "qqq_capitulation_buy",
        "name":    "QQQ — buy the capitulation, not the dip",
        "thesis":  (
            "Median oil shock = -23% S&P. We are at -6.7%. "
            "Wait for VIX >40 capitulation and QQQ down >20%. Do not anticipate."
        ),
        "instrument": "QQQ",
        "strike":     "N/A",
        "expiry":     "N/A",
        "account":    "Taxable / 401k",
        "size":       "5-8% of taxable on confirmed capitulation",
        "entry_conditions": [
            "vix >= 40",
            "qqq_from_peak <= -20%",
            "oil_stabilizing == True",
        ],
        "entry_logic": "AND — all three required",
        "exit_profit":  "12-month hold minimum — long-term entry",
        "exit_stop":    "VIX spikes again >40 within 3 months — add more (scale in)",
        "status":       "monitoring",
        "tickers":      ["QQQ", "NVDA", "MSFT", "GOOGL"],
    },
]

# ─── Weekly prediction ledger schema ──────────────────────────────────────────

LEDGER_SCHEMA = {
    "version": "1.0",
    "entry_fields": [
        "week_start", "week_end", "conflict_day_start",
        "hypotheses", "outcomes", "model_signals",
        "notes", "scenario_at_start", "scenario_at_end",
    ],
    "hypothesis_fields": [
        "id", "statement", "signal_basis",
        "direction", "target", "confidence",
    ],
    "outcome_fields": [
        "hypothesis_id", "what_happened", "score",
        "model_predicted", "missed_signal",
    ],
}

LEDGER_SCORING = {
    2:  "Direction + magnitude both correct",
    1:  "Direction correct, magnitude off",
    0:  "Wrong direction",
    -1: "Confidently wrong — acted on it and lost",
}

LEDGER_ACCURACY_THRESHOLDS = {
    "excellent": 0.75,
    "good":      0.60,
    "review":    0.50,
    "rebuild":   0.00,
}

# ─── Display settings ─────────────────────────────────────────────────────────

REFRESH_INTERVALS = {
    "tier1_minutes": 15,
    "tier2_hours":   24,
    "cache_hours":   1,
}

SPARKLINE_DAYS = 20
APP_TITLE      = "Macro Signal Ledger"
APP_ICON       = "📡"
APP_SUBTITLE   = "Burry engine v1 · March 2026"

OVERNIGHT_TRANSMISSION = {
    "kospi_to_sp500":  0.25,
    "nikkei_to_sp500": 0.18,
    "europe_to_sp500": 0.30,
    "data_points":     1,
    "next_refinement": "after 30 data points",
}

GEO_INTENSITY_WEIGHTS = {
    "oil_vs_90d_avg": 30,
    "ovx_level":      20,
    "defense_vs_sp":  20,
    "vix_vs_20d_avg": 30,
}

GEO_INTENSITY_THRESHOLDS = {
    "normal":   (0,  40),
    "elevated": (40, 60),
    "warning":  (60, 80),
    "critical": (80, 100),
}
