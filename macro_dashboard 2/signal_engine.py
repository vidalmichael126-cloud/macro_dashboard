"""
signal_engine.py — The intellectual core of the dashboard.
Translates raw prices into statuses, fires combination rules,
and scores scenario probabilities. No UI code here — pure logic.
"""

from config import (
    THRESHOLDS, COMBINATION_RULES, SCENARIOS,
    SCENARIO_SCORING_RULES, STATUS_LEVELS,
    GEO_INTENSITY_WEIGHTS, GEO_INTENSITY_THRESHOLDS,
    OVERNIGHT_TRANSMISSION, STRUCTURAL_PRIORS,
)
from data_feeds import (
    fetch_live_prices, fetch_all_fred,
    get_current_value, get_xle_oil_divergence, get_dollar_falling,
    get_200day_ma, get_overnight_signals, get_signal_momentum, get_iwm_spy_ratio,
    # New — Burry engine
    get_pe_basket, get_hyg_credit_stress, get_gold_tracker,
    get_japan_10y, get_episode_score, evaluate_action_triggers,
)


# ─── Signal status evaluation ─────────────────────────────────────────────────

def get_signal_status(signal_name: str, value: float) -> str:
    """
    Return the status string for a signal given its current value.
    Uses THRESHOLDS from config.py.
    Returns: "normal" | "elevated" | "warning" | "critical"
    """
    if signal_name not in THRESHOLDS or value is None:
        return "normal"

    thresholds = THRESHOLDS[signal_name]

    # Check from most severe down to normal
    for level in ["critical", "warning", "elevated", "normal"]:
        lo, hi = thresholds[level]
        if lo <= value < hi:
            return level

    return "normal"


def get_all_signal_statuses(prices: dict, fred: dict) -> dict:
    """
    Evaluate all tracked signals and return their current status.
    Returns: { signal_name: {"value": float, "status": str, "meta": dict} }
    """
    statuses = {}

    # Market data signals
    signal_map = {
        "oil":         ("oil",      "price"),
        "vix":         ("vix",      "price"),
        "yield_10":    ("yield_10", "price"),
        "usdjpy":      ("usdjpy",   "price"),
    }

    for signal_name, (ticker_key, field) in signal_map.items():
        value = get_current_value(prices, ticker_key, field)

        # For yield_10, Yahoo's ^TNX returns in basis points (multiply by 0.1)
        if signal_name == "yield_10" and value is not None:
            value = round(value * 0.1, 2) if value > 20 else value

        status = get_signal_status(signal_name, value)
        meta   = THRESHOLDS.get(signal_name, {})

        statuses[signal_name] = {
            "value":       value,
            "status":      status,
            "status_level": STATUS_LEVELS.get(status, 0),
            "description": meta.get("description", signal_name),
            "unit":        meta.get("unit", ""),
            "note":        meta.get("note", ""),
        }

    # Yield curve from FRED
    curve_series = fred.get("yield_curve")
    curve_val    = float(curve_series.iloc[-1]) if curve_series is not None and len(curve_series) > 0 else None
    statuses["yield_curve"] = {
        "value":       curve_val,
        "status":      get_signal_status("yield_curve", curve_val),
        "status_level": STATUS_LEVELS.get(get_signal_status("yield_curve", curve_val), 0),
        "description": "2s10s yield curve (10yr − 2yr)",
        "unit":        "%",
        "note":        "Negative = inverted = recession signal",
    }

    # XLE-oil divergence (special computed signal)
    divergence = get_xle_oil_divergence(prices)
    statuses["xle_divergence"] = {
        "value":        divergence["xle_change"],
        "status":       "warning" if divergence["diverging"] else "normal",
        "status_level": 2 if divergence["diverging"] else 0,
        "description":  "XLE vs oil divergence (early peace signal)",
        "unit":         "% gap",
        "note":         divergence["note"],
        "diverging":    divergence["diverging"],
    }

    # ── New: HYG credit stress ────────────────────────────────────────────────
    hyg_stress = get_hyg_credit_stress()
    hyg_5d_ret = hyg_stress.get("hyg_5d_ret", 0) if hyg_stress.get("ok") else 0
    statuses["hyg_credit"] = {
        "value":            hyg_5d_ret,
        "status":           hyg_stress.get("status", "normal"),
        "status_level":     STATUS_LEVELS.get(hyg_stress.get("status", "normal"), 0),
        "description":      "HYG 5-day return — PE debt cost signal",
        "unit":             "%",
        "note":             THRESHOLDS["hyg_5d"].get("note", ""),
        "consecutive_down": hyg_stress.get("consecutive_down", 0),
        "raw":              hyg_stress,
    }

    # ── New: PE basket vs SPY ─────────────────────────────────────────────────
    pe_data = get_pe_basket()
    pe_spread = pe_data.get("spread", 0) if pe_data.get("ok") else 0
    statuses["pe_basket"] = {
        "value":        pe_spread,
        "status":       pe_data.get("status", "normal"),
        "status_level": STATUS_LEVELS.get(pe_data.get("status", "normal"), 0),
        "description":  "PE basket (BX/KKR/APO/ARES/OWL) vs SPY 10d",
        "unit":         "% spread",
        "note":         "Negative = PE underperforming SPY. < −5% = Burry entry threshold.",
        "lagging":      pe_data.get("lagging", False),
        "raw":          pe_data,
    }

    # ── New: Gold 1979 tracker ────────────────────────────────────────────────
    gold_data = get_gold_tracker()
    gold_60d  = gold_data.get("ret_60d", 0) if gold_data.get("ok") else 0
    statuses["gold_tracker"] = {
        "value":           gold_60d,
        "status":          gold_data.get("status", "normal"),
        "status_level":    STATUS_LEVELS.get(gold_data.get("status", "normal"), 0),
        "description":     "Gold 60d return — 1979 parabolic tracker",
        "unit":            "%",
        "note":            gold_data.get("analog_note", ""),
        "pattern_active":  gold_data.get("pattern_active", False),
        "reversal_risk":   gold_data.get("reversal_risk", False),
        "in_add_zone":     gold_data.get("in_add_zone", False),
        "pct_from_high":   gold_data.get("pct_from_high", 0),
        "raw":             gold_data,
    }

    # ── New: Japan 10yr yield ─────────────────────────────────────────────────
    jp10y_data = get_japan_10y()
    jp10y_val  = jp10y_data.get("jp10y", 0) if jp10y_data.get("ok") else 0
    statuses["jp10y"] = {
        "value":        jp10y_val,
        "status":       jp10y_data.get("status", "normal"),
        "status_level": STATUS_LEVELS.get(jp10y_data.get("status", "normal"), 0),
        "description":  "Japan 10yr yield — BoJ cap / Treasury selloff mechanism",
        "unit":         "%",
        "note":         THRESHOLDS["jp10y"].get("note", ""),
        "above_boj_cap": jp10y_data.get("above_boj_cap", False),
        "boj_cap_pct":  jp10y_data.get("boj_cap_pct", 0),
        "raw":          jp10y_data,
    }

    # ── New: Episode tracker ──────────────────────────────────────────────────
    episode_data = get_episode_score()
    statuses["episode_tracker"] = {
        "value":          episode_data.get("confidence", 0),
        "status":         "elevated" if episode_data.get("confidence", 0) > 0.4 else "normal",
        "status_level":   1 if episode_data.get("confidence", 0) > 0.4 else 0,
        "description":    "Historical analog tracker",
        "unit":           "confidence",
        "best_match":     episode_data.get("best_match", "unknown"),
        "label":          episode_data.get("label", "Insufficient data"),
        "scenario_weight": episode_data.get("scenario_weight", "B"),
        "note":           episode_data.get("note", ""),
        "scores":         episode_data.get("scores", {}),
        "raw":            episode_data,
    }

    return statuses


# ─── Combination rule evaluation ──────────────────────────────────────────────

def evaluate_combination_rules(statuses: dict, prices: dict) -> list:
    """
    Check all combination rules against current signal statuses.
    Returns a list of dicts for rules that are currently active or near-active.
    """
    active_rules   = []
    watching_rules = []
    dollar_falling = get_dollar_falling(prices)

    for rule in COMBINATION_RULES:
        # Handle special computed rules
        if rule.get("special") == "xle_oil_divergence":
            div_status = statuses.get("xle_divergence", {})
            if div_status.get("diverging", False):
                active_rules.append({
                    **rule,
                    "state": "active",
                    "note":  div_status.get("note", ""),
                })
            continue

        if rule.get("special") == "sp500_200day_break":
            ma_check = statuses.get("sp500_200d_break", {})
            if ma_check.get("firing", False):
                active_rules.append({
                    **rule,
                    "state": "active",
                    "note":  ma_check.get("note", ""),
                })
            continue

        if rule.get("special") == "recession_regime":
            rec_check = statuses.get("recession_regime", {})
            if rec_check.get("firing", False):
                active_rules.append({
                    **rule,
                    "state": "active",
                    "note":  rec_check.get("note", ""),
                })
            continue

        # Evaluate standard condition-based rules
        conditions_met = []
        conditions_total = len(rule["conditions"])

        for signal, min_level in rule["conditions"].items():
            current_level = statuses.get(signal, {}).get("status", "normal")
            if STATUS_LEVELS.get(current_level, 0) >= STATUS_LEVELS.get(min_level, 0):
                conditions_met.append(signal)

        # Check additional conditions
        if rule.get("additional_check") == "dollar_falling":
            if dollar_falling:
                conditions_met.append("dollar_falling")
            conditions_total += 1

        conditions_count = len(conditions_met)

        if conditions_count == conditions_total and conditions_total > 0:
            active_rules.append({
                **rule,
                "state":           "active",
                "conditions_met":  conditions_met,
                "conditions_total": conditions_total,
            })
        elif conditions_count >= max(1, conditions_total - 1):
            # Near-active: all but one condition met
            missing = [c for c in list(rule["conditions"].keys()) + 
                       (["dollar_falling"] if rule.get("additional_check") == "dollar_falling" else [])
                       if c not in conditions_met]
            watching_rules.append({
                **rule,
                "state":           "watch",
                "conditions_met":  conditions_met,
                "conditions_total": conditions_total,
                "missing":         missing,
            })

    return active_rules + watching_rules


# ─── Scenario probability scoring ─────────────────────────────────────────────

def score_scenarios(statuses: dict, prices: dict) -> dict:
    """
    Start from default probabilities and adjust based on current signal states.
    Returns { "A": int, "B": int, "C": int } that sum to 100.
    """
    probs = {
        "A": SCENARIOS["A"]["probability_default"],
        "B": SCENARIOS["B"]["probability_default"],
        "C": SCENARIOS["C"]["probability_default"],
    }

    oil_val    = statuses.get("oil",    {}).get("value")
    vix_val    = statuses.get("vix",    {}).get("value")
    yield_val  = statuses.get("yield_10", {}).get("value")
    usdjpy_val = statuses.get("usdjpy", {}).get("value")
    xle_div    = statuses.get("xle_divergence", {}).get("diverging", False)

    # Build condition flags
    conditions = {
        # ── Existing conditions ───────────────────────────────────────────────
        "oil_above_150":  oil_val is not None and oil_val > 150,
        "oil_above_120":  oil_val is not None and oil_val > 120,
        "oil_below_90":   oil_val is not None and oil_val < 90,
        "vix_above_40":   vix_val is not None and vix_val > 40,
        "vix_below_20":   vix_val is not None and vix_val < 20,
        "xle_diverging":  xle_div,
        "yield_above_5":  yield_val is not None and yield_val > 5.0,
        "usdjpy_critical": usdjpy_val is not None and usdjpy_val > 155,
        "sp500_below_200d": statuses.get("sp500_200d_break", {}).get("firing", False),
        "recession_confirmed": statuses.get("recession_regime", {}).get("firing", False),
        # ── New: PE and credit stress ─────────────────────────────────────────
        "pe_stress_confirmed": (
            statuses.get("pe_basket", {}).get("lagging", False)
            and statuses.get("hyg_credit", {}).get("status") in ["warning", "critical"]
        ),
        "hyg_stress": statuses.get("hyg_credit", {}).get("status") in ["elevated", "warning", "critical"],
        # ── New: Gold 1979 pattern ────────────────────────────────────────────
        "gold_1979_active": statuses.get("gold_tracker", {}).get("pattern_active", False),
        # ── New: Japan Treasury pressure ──────────────────────────────────────
        "japan_pressure": (
            statuses.get("jp10y", {}).get("above_boj_cap", False)
            and usdjpy_val is not None and usdjpy_val > 148
        ),
        # ── New: Historical episode analog weights ────────────────────────────
        "analog_1973": (
            statuses.get("episode_tracker", {}).get("best_match") == "1973"
            and statuses.get("episode_tracker", {}).get("value", 0) >= 0.4
        ),
        "analog_1990": (
            statuses.get("episode_tracker", {}).get("best_match") == "1990"
            and statuses.get("episode_tracker", {}).get("value", 0) >= 0.4
        ),
    }

    # Apply scoring adjustments
    for rule in SCENARIO_SCORING_RULES:
        if conditions.get(rule["condition"], False):
            for scenario in ["A", "B", "C"]:
                probs[scenario] += rule[scenario]

    # Normalize to sum to 100, clamp to [1, 97]
    total = sum(probs.values())
    if total > 0:
        probs = {k: max(1, round(v * 100 / total)) for k, v in probs.items()}

    # Fix rounding error — ensure exactly 100
    diff = 100 - sum(probs.values())
    if diff != 0:
        dominant = max(probs, key=probs.get)
        probs[dominant] += diff

    return probs


# ─── Current scenario determination ───────────────────────────────────────────

def get_current_scenario(probs: dict) -> str:
    """Return the most likely scenario letter."""
    return max(probs, key=probs.get)


def get_scenario_color(scenario: str) -> dict:
    """Return color dict for a scenario."""
    return SCENARIOS.get(scenario, SCENARIOS["B"])


# ─── Status color helpers ──────────────────────────────────────────────────────

STATUS_COLORS = {
    "normal":    {"bg": "#EAF3DE", "border": "#639922", "text": "#27500A", "label": "Normal"},
    "elevated":  {"bg": "#FAEEDA", "border": "#EF9F27", "text": "#633806", "label": "Elevated"},
    "warning":   {"bg": "#FCEBEB", "border": "#E24B4A", "text": "#791F1F", "label": "Warning"},
    "critical":  {"bg": "#FCEBEB", "border": "#A32D2D", "text": "#501313", "label": "Critical"},
    "active":    {"bg": "#FCEBEB", "border": "#E24B4A", "text": "#791F1F", "label": "Active"},
    "watch":     {"bg": "#FAEEDA", "border": "#EF9F27", "text": "#633806", "label": "Watch"},
    "opportunity": {"bg": "#E6F1FB", "border": "#185FA5", "text": "#042C53", "label": "Opportunity"},
    "working":   {"bg": "#EAF3DE", "border": "#639922", "text": "#27500A", "label": "Working"},
}

SEVERITY_COLORS = {
    "critical":    STATUS_COLORS["critical"],
    "warning":     STATUS_COLORS["warning"],
    "opportunity": STATUS_COLORS["opportunity"],
}


def status_color(status: str) -> dict:
    return STATUS_COLORS.get(status, STATUS_COLORS["normal"])


# ─── New: Geopolitical intensity score ────────────────────────────────────────

def score_geopolitical_intensity(prices: dict) -> dict:
    """
    Composite 0–100 score measuring how much geopolitical risk is priced in.
    Inputs: oil vs 90d average, OVX level, defense vs SPY, VIX vs 20d average.
    Score <40 = normal, 40–60 = elevated, 60–80 = warning, 80+ = critical.
    """
    score = 0
    components = {}

    # Component 1: Oil vs 90-day average (max 30 pts)
    try:
        oil_hist = __import__("yfinance").Ticker("CL=F").history(period="95d")
        if len(oil_hist) >= 90:
            avg_90d   = float(oil_hist["Close"].iloc[-90:].mean())
            current   = float(oil_hist["Close"].iloc[-1])
            pct_above = max(0, (current - avg_90d) / avg_90d * 100)
            pts       = min(30, pct_above * 1.2)  # 25% above avg = full 30 pts
            score += pts
            components["oil_vs_90d"] = round(pts, 1)
    except Exception:
        components["oil_vs_90d"] = 0

    # Component 2: OVX level (max 20 pts)
    # OVX <25 = calm, 25–40 = elevated, 40–60 = high, 60+ = extreme
    ovx_val = get_current_value(prices, "ovx", "price")
    if ovx_val:
        pts = min(20, max(0, (ovx_val - 25) / 2))
        score += pts
        components["ovx"] = round(pts, 1)
    else:
        components["ovx"] = 0

    # Component 3: Defense (ITA) vs SPY 5-day relative performance (max 20 pts)
    try:
        ita_h = __import__("yfinance").Ticker("ITA").history(period="10d")
        spy_h = __import__("yfinance").Ticker("SPY").history(period="10d")
        if len(ita_h) >= 5 and len(spy_h) >= 5:
            ita_ret = (float(ita_h["Close"].iloc[-1]) / float(ita_h["Close"].iloc[-5]) - 1) * 100
            spy_ret = (float(spy_h["Close"].iloc[-1]) / float(spy_h["Close"].iloc[-5]) - 1) * 100
            outperf = max(0, ita_ret - spy_ret)  # Defense outperforming = conflict pricing
            pts     = min(20, outperf * 4)        # 5% outperformance = full 20 pts
            score  += pts
            components["defense_vs_spy"] = round(pts, 1)
    except Exception:
        components["defense_vs_spy"] = 0

    # Component 4: VIX vs its own 20-day average (max 30 pts)
    try:
        vix_h = __import__("yfinance").Ticker("^VIX").history(period="30d")
        if len(vix_h) >= 20:
            avg_20d = float(vix_h["Close"].iloc[-20:].mean())
            current = float(vix_h["Close"].iloc[-1])
            pct_above = max(0, (current - avg_20d) / avg_20d * 100)
            pts     = min(30, pct_above * 0.75)  # 40% above avg = full 30 pts
            score  += pts
            components["vix_vs_20d"] = round(pts, 1)
    except Exception:
        components["vix_vs_20d"] = 0

    total = min(100, round(score))

    # Map score to status
    status = "normal"
    for s, (lo, hi) in GEO_INTENSITY_THRESHOLDS.items():
        if lo <= total < hi:
            status = s
            break

    return {
        "score":      total,
        "status":     status,
        "components": components,
    }


# ─── New: 200-day break checker ───────────────────────────────────────────────

def check_200day_break(ma_data: dict) -> dict:
    """
    Determine if S&P 500 is in a 200-day MA break state.
    Returns firing status for the combination rule engine.
    """
    if not ma_data.get("ok"):
        return {"firing": False, "note": "Data unavailable"}

    above   = ma_data.get("above_200d", True)
    streak  = ma_data.get("streak_days", 0)
    pct     = ma_data.get("pct_from_ma", 0)

    if not above:
        note = (f"S&P 500 is {abs(pct):.1f}% below its 200-day MA · "
                f"{streak} session{'s' if streak != 1 else ''} below · "
                f"Institutional algorithms in sell mode")
        return {"firing": True, "streak": streak, "pct": pct, "note": note}
    else:
        note = (f"S&P 500 is {pct:.1f}% above its 200-day MA · "
                f"{streak} session streak · Support intact")
        return {"firing": False, "streak": streak, "pct": pct, "note": note}


# ─── New: Recession regime detector ──────────────────────────────────────────

def check_recession_regime(iwm_data: dict, statuses: dict) -> dict:
    """
    Detect whether market is pricing a recessionary outcome vs stagflation.
    Recession pricing: small caps underperforming, yield curve stressed,
    AND the selloff is broad (not just energy-related).
    """
    if not iwm_data.get("ok"):
        return {"firing": False, "probability": 0, "note": "Data unavailable"}

    signals = 0
    reasons = []

    # Small caps underperforming large caps by 2%+
    if iwm_data.get("underperforming"):
        signals += 1
        spread = iwm_data.get("spread", 0)
        reasons.append(f"IWM lagging SPY by {abs(spread):.1f}% over 5 days")

    # Yield curve inverted
    curve_status = statuses.get("yield_curve", {}).get("status", "normal")
    if curve_status in ["elevated", "warning", "critical"]:
        signals += 1
        reasons.append("Yield curve inverted — recession historically follows")

    # HYG credit spreads widening (HYG falling)
    hyg_chg = get_current_value(
        __import__("data_feeds").fetch_live_prices(), "hyg", "change_pct"
    ) or 0
    if hyg_chg < -0.5:
        signals += 1
        reasons.append(f"HYG down {abs(hyg_chg):.1f}% — credit spreads widening")

    firing      = signals >= 2
    probability = min(100, signals * 33)

    note = " · ".join(reasons) if reasons else "No recession signals firing"
    return {
        "firing":      firing,
        "signals":     signals,
        "probability": probability,
        "note":        note,
    }


# ─── New: Overnight predictive open estimate ─────────────────────────────────

def estimate_sp500_open(overnight: dict) -> dict:
    """
    Use Asian close + European open data with transmission coefficients
    to estimate where S&P 500 will open.
    Coefficient: 0.25 (KOSPI), 0.18 (Nikkei), 0.30 (Europe).
    Hardcoded based on March 2026 conflict week observation.
    Refine after 30+ data points.
    """
    votes    = []
    details  = []

    ewy = overnight.get("ewy", {})
    if ewy.get("ok") and ewy.get("change_pct") is not None:
        est = ewy["change_pct"] * OVERNIGHT_TRANSMISSION["kospi_to_sp500"]
        votes.append(est)
        direction = "↑" if ewy["change_pct"] > 0 else "↓"
        details.append(f"KOSPI {direction}{abs(ewy['change_pct']):.1f}% → {est:+.2f}% S&P est")

    ewj = overnight.get("ewj", {})
    if ewj.get("ok") and ewj.get("change_pct") is not None:
        est = ewj["change_pct"] * OVERNIGHT_TRANSMISSION["nikkei_to_sp500"]
        votes.append(est)
        direction = "↑" if ewj["change_pct"] > 0 else "↓"
        details.append(f"Nikkei {direction}{abs(ewj['change_pct']):.1f}% → {est:+.2f}% S&P est")

    fez = overnight.get("fez", {})
    if fez.get("ok") and fez.get("change_pct") is not None:
        est = fez["change_pct"] * OVERNIGHT_TRANSMISSION["europe_to_sp500"]
        votes.append(est)
        direction = "↑" if fez["change_pct"] > 0 else "↓"
        details.append(f"Europe {direction}{abs(fez['change_pct']):.1f}% → {est:+.2f}% S&P est")

    if not votes:
        return {"estimate": None, "direction": "unknown", "details": []}

    avg_est   = sum(votes) / len(votes)
    direction = "higher" if avg_est > 0.1 else "lower" if avg_est < -0.1 else "flat"

    return {
        "estimate":  round(avg_est, 2),
        "direction": direction,
        "details":   details,
        "note":      f"Model estimate: S&P opens {direction} by ~{abs(avg_est):.1f}% · Coefficient 0.25 (KOSPI), 0.18 (Nikkei), 0.30 (Europe)",
    }


# ─── Full analysis bundle ─────────────────────────────────────────────────────

def _build_prob_drivers(statuses: dict, probs: dict) -> list:
    """
    Build a human-readable list of what drove the scenario probabilities.
    Returns list of { condition, fired, impact_a, impact_b, impact_c, note }
    so the UI can show exactly why B is at 54% and not 47%.
    """
    from config import SCENARIO_SCORING_RULES, STRUCTURAL_PRIORS

    drivers = []

    # Always show structural prior first
    drivers.append({
        "condition":  "Debt/GDP structural prior",
        "fired":      True,
        "impact_a":   STRUCTURAL_PRIORS["scenario_a_bias"],
        "impact_b":   STRUCTURAL_PRIORS["scenario_b_bias"],
        "impact_c":   STRUCTURAL_PRIORS["scenario_c_bias"],
        "note":       f"102% debt/GDP — permanent Dalio prior. Fed cannot Volcker this.",
        "type":       "structural",
    })

    # Evaluate each scoring rule
    oil_val    = statuses.get("oil",     {}).get("value")
    vix_val    = statuses.get("vix",     {}).get("value")
    yield_val  = statuses.get("yield_10",{}).get("value")
    usdjpy_val = statuses.get("usdjpy",  {}).get("value")
    xle_div    = statuses.get("xle_divergence", {}).get("diverging", False)

    condition_map = {
        "oil_above_150":       (oil_val is not None and oil_val > 150,       f"Oil ${oil_val:.0f} > $150"),
        "oil_above_120":       (oil_val is not None and oil_val > 120,       f"Oil ${oil_val:.0f} > $120"),
        "oil_below_90":        (oil_val is not None and oil_val < 90,        f"Oil ${oil_val:.0f} < $90"),
        "vix_above_40":        (vix_val is not None and vix_val > 40,        f"VIX {vix_val:.1f} > 40"),
        "vix_below_20":        (vix_val is not None and vix_val < 20,        f"VIX {vix_val:.1f} < 20"),
        "xle_diverging":       (xle_div,                                      "XLE/oil divergence detected"),
        "yield_above_5":       (yield_val is not None and yield_val > 5.0,   f"10yr yield {yield_val:.2f}% > 5%"),
        "usdjpy_critical":     (usdjpy_val is not None and usdjpy_val > 155, f"USD/JPY {usdjpy_val:.1f} > 155"),
        "sp500_below_200d":    (statuses.get("sp500_200d_break", {}).get("firing", False), "S&P below 200-day MA"),
        "recession_confirmed": (statuses.get("recession_regime", {}).get("firing", False), "Recession pricing active"),
        "pe_stress_confirmed": (
            statuses.get("pe_basket", {}).get("lagging", False)
            and statuses.get("hyg_credit", {}).get("status") in ["warning", "critical"],
            "PE basket lagging + HYG falling"
        ),
        "hyg_stress":          (statuses.get("hyg_credit", {}).get("status") in ["elevated", "warning", "critical"], "HYG credit stress"),
        "gold_1979_active":    (statuses.get("gold_tracker", {}).get("pattern_active", False), "Gold 1979 pattern active"),
        "japan_pressure":      (
            statuses.get("jp10y", {}).get("above_boj_cap", False) and usdjpy_val is not None and usdjpy_val > 148,
            "Japan JGB above BoJ cap + USD/JPY > 148"
        ),
        "analog_1973":         (
            statuses.get("episode_tracker", {}).get("best_match") == "1973"
            and statuses.get("episode_tracker", {}).get("value", 0) >= 0.4,
            "Episode tracker: 1973 analog confirmed"
        ),
        "analog_1990":         (
            statuses.get("episode_tracker", {}).get("best_match") == "1990"
            and statuses.get("episode_tracker", {}).get("value", 0) >= 0.4,
            "Episode tracker: 1990 analog confirmed"
        ),
    }

    for rule in SCENARIO_SCORING_RULES:
        cond = rule["condition"]
        if cond not in condition_map:
            continue
        fired, note = condition_map[cond]
        if fired or True:   # show all rules, fired or not, for transparency
            drivers.append({
                "condition": cond,
                "fired":     fired,
                "impact_a":  rule["A"] if fired else 0,
                "impact_b":  rule["B"] if fired else 0,
                "impact_c":  rule["C"] if fired else 0,
                "raw_a":     rule["A"],
                "raw_b":     rule["B"],
                "raw_c":     rule["C"],
                "note":      note,
                "type":      "signal",
            })

    return drivers


def get_full_analysis() -> dict:
    """
    Single call that returns everything the views need.
    Now includes: PE basket, HYG credit stress, gold 1979 tracker,
    Japan 10yr, episode tracker, action triggers, and structural priors.
    """
    prices   = fetch_live_prices()
    fred     = fetch_all_fred()
    statuses = get_all_signal_statuses(prices, fred)
    # get_all_signal_statuses now calls all new feeds internally
    # and injects them into statuses — pull them back out for convenience

    # ── Core existing signals ────────────────────────────────────────────────
    ma_data   = get_200day_ma()
    ma_break  = check_200day_break(ma_data)
    iwm_data  = get_iwm_spy_ratio()
    momentum  = get_signal_momentum()
    geo_score = score_geopolitical_intensity(prices)
    overnight = get_overnight_signals()
    open_est  = estimate_sp500_open(overnight)
    rec_check = check_recession_regime(iwm_data, statuses)

    # Inject structural computed signals into statuses
    statuses["sp500_200d_break"] = {**ma_break,  "description": "S&P 500 vs 200-day MA"}
    statuses["recession_regime"] = {**rec_check, "description": "Recession regime detector"}
    statuses["geo_intensity"]    = {
        "value":       geo_score["score"],
        "status":      geo_score["status"],
        "description": "Geopolitical intensity score (0–100)",
        "unit":        "/100",
        "components":  geo_score["components"],
    }

    # Add momentum arrows to primary signal statuses
    for sig, direction in momentum.items():
        if sig in statuses:
            statuses[sig]["momentum"] = direction

    # ── New: Burry engine signals ─────────────────────────────────────────────
    # Already fetched inside get_all_signal_statuses — retrieve from statuses
    pe_data   = statuses.get("pe_basket",     {}).get("raw", {})
    hyg_data  = statuses.get("hyg_credit",    {}).get("raw", {})
    gold_data = statuses.get("gold_tracker",  {}).get("raw", {})
    jp10y_data = statuses.get("jp10y",        {}).get("raw", {})
    episode   = statuses.get("episode_tracker",{}).get("raw", {})

    # ── Action triggers ───────────────────────────────────────────────────────
    action_signal_states = {
        "hyg_credit":    hyg_data,
        "pe_basket":     pe_data,
        "gold":          gold_data,
        "ma200":         ma_data,
        "jp10y":         jp10y_data,
        "xle_divergence": statuses.get("xle_divergence", {}),
        "momentum":      momentum,
    }
    action_triggers = evaluate_action_triggers(prices, action_signal_states)

    # ── Score scenarios with all new conditions active ────────────────────────
    rules    = evaluate_combination_rules(statuses, prices)
    probs    = score_scenarios(statuses, prices)
    scenario = get_current_scenario(probs)

    # ── Build probability explanation ─────────────────────────────────────────
    prob_drivers = _build_prob_drivers(statuses, probs)

    return {
        # Core
        "prices":          prices,
        "fred":            fred,
        "statuses":        statuses,
        "rules":           rules,
        "probs":           probs,
        "prob_drivers":    prob_drivers,
        "scenario":        scenario,
        # Structural
        "ma_data":         ma_data,
        "momentum":        momentum,
        "geo_score":       geo_score,
        "overnight":       overnight,
        "open_est":        open_est,
        "iwm_data":        iwm_data,
        # New: Burry engine
        "pe_data":         pe_data,
        "hyg_data":        hyg_data,
        "gold_data":       gold_data,
        "jp10y_data":      jp10y_data,
        "episode":         episode,
        "action_triggers": action_triggers,
        # Model meta
        "structural_priors": STRUCTURAL_PRIORS,
        "conflict_day":    23,   # TODO: compute from conflict start date
    }
