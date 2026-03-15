"""
signal_engine.py — The intellectual core of the dashboard.
Translates raw prices into statuses, fires combination rules,
and scores scenario probabilities. No UI code here — pure logic.
"""

from config import (
    THRESHOLDS, COMBINATION_RULES, SCENARIOS,
    SCENARIO_SCORING_RULES, STATUS_LEVELS
)
from data_feeds import (
    fetch_live_prices, fetch_all_fred,
    get_current_value, get_xle_oil_divergence, get_dollar_falling
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
        "oil_above_150":  oil_val is not None and oil_val > 150,
        "oil_above_120":  oil_val is not None and oil_val > 120,
        "oil_below_90":   oil_val is not None and oil_val < 90,
        "vix_above_40":   vix_val is not None and vix_val > 40,
        "vix_below_20":   vix_val is not None and vix_val < 20,
        "xle_diverging":  xle_div,
        "yield_above_5":  yield_val is not None and yield_val > 5.0,
        "usdjpy_critical": usdjpy_val is not None and usdjpy_val > 155,
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


# ─── Full analysis bundle ─────────────────────────────────────────────────────

def get_full_analysis() -> dict:
    """
    Single call that returns everything the views need.
    Caches intermediate results via the individual fetch functions.
    """
    prices    = fetch_live_prices()
    fred      = fetch_all_fred()
    statuses  = get_all_signal_statuses(prices, fred)
    rules     = evaluate_combination_rules(statuses, prices)
    probs     = score_scenarios(statuses, prices)
    scenario  = get_current_scenario(probs)

    return {
        "prices":   prices,
        "fred":     fred,
        "statuses": statuses,
        "rules":    rules,
        "probs":    probs,
        "scenario": scenario,
    }
