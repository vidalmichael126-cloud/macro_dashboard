"""
prediction_ledger.py — Weekly hypothesis → outcome → accuracy tracking.
Uses Streamlit persistent storage (cloud-safe, survives redeployments).
Falls back to local JSON if storage API unavailable.

Storage key: "ledger_v1"
Schema: { "weeks": [ { week entry }, ... ] }
"""

import json
import streamlit as st
from datetime import datetime, date, timedelta
from config import LEDGER_SCHEMA, LEDGER_SCORING, LEDGER_ACCURACY_THRESHOLDS


# ─── Storage helpers ──────────────────────────────────────────────────────────

STORAGE_KEY = "macro_ledger_v1"

def _load_ledger() -> dict:
    """Load ledger from Streamlit persistent storage. Returns empty ledger on miss."""
    try:
        result = st.context.storage.get(STORAGE_KEY)
        if result and result.get("value"):
            return json.loads(result["value"])
    except Exception:
        pass
    # Also check session state as in-memory fallback
    if "ledger_data" in st.session_state:
        return st.session_state["ledger_data"]
    return {"weeks": [], "schema_version": "1.0"}


def _save_ledger(data: dict) -> bool:
    """Save ledger to Streamlit persistent storage + session state."""
    st.session_state["ledger_data"] = data
    try:
        st.context.storage.set(STORAGE_KEY, json.dumps(data))
        return True
    except Exception:
        pass
    return False


def export_ledger_json() -> str:
    """Return full ledger as formatted JSON string for download."""
    data = _load_ledger()
    return json.dumps(data, indent=2, default=str)


# ─── Week helpers ─────────────────────────────────────────────────────────────

def _week_key(dt: date = None) -> str:
    """Return ISO week key string: '2026-W12'"""
    dt = dt or date.today()
    return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"


def _week_monday(dt: date = None) -> date:
    dt = dt or date.today()
    return dt - timedelta(days=dt.weekday())


def _week_friday(dt: date = None) -> date:
    return _week_monday(dt) + timedelta(days=4)


def get_current_week_key() -> str:
    return _week_key()


def get_week_label(week_key: str) -> str:
    """Human readable: 'Week of Mar 23–28, 2026'"""
    try:
        year, wnum = week_key.split("-W")
        mon = date.fromisocalendar(int(year), int(wnum), 1)
        fri = mon + timedelta(days=4)
        if mon.month == fri.month:
            return f"Week of {mon.strftime('%b')} {mon.day}–{fri.day}, {mon.year}"
        return f"Week of {mon.strftime('%b')} {mon.day}–{fri.strftime('%b')} {fri.day}, {mon.year}"
    except Exception:
        return week_key


# ─── CRUD operations ──────────────────────────────────────────────────────────

def get_or_create_week(week_key: str = None) -> dict:
    """Get the week entry, creating it if it doesn't exist."""
    week_key = week_key or get_current_week_key()
    data = _load_ledger()
    for week in data["weeks"]:
        if week["week_key"] == week_key:
            return week
    # Create new week
    mon = _week_monday()
    new_week = {
        "week_key":        week_key,
        "week_label":      get_week_label(week_key),
        "week_start":      str(_week_monday()),
        "week_end":        str(_week_friday()),
        "conflict_day":    23,     # TODO: compute dynamically
        "scenario_start":  None,
        "scenario_end":    None,
        "hypotheses":      [],
        "notes":           "",
        "scored":          False,
        "accuracy_pct":    None,
    }
    data["weeks"].insert(0, new_week)   # newest first
    _save_ledger(data)
    return new_week


def add_hypothesis(statement: str, target: str, direction: str,
                   signals: list, confidence: int, week_key: str = None) -> bool:
    """Add a hypothesis to the current week."""
    if not statement.strip():
        return False
    week_key = week_key or get_current_week_key()
    data     = _load_ledger()

    hyp = {
        "id":        f"h{int(datetime.now().timestamp())}",
        "statement": statement.strip(),
        "target":    target.strip(),
        "direction": direction,
        "signals":   signals,
        "confidence": confidence,
        "filed_at":  str(datetime.now()),
        "outcome":   None,   # filled during Friday review
        "score":     None,
    }

    for week in data["weeks"]:
        if week["week_key"] == week_key:
            week["hypotheses"].append(hyp)
            _save_ledger(data)
            return True
    return False


def delete_hypothesis(hyp_id: str, week_key: str = None) -> bool:
    """Remove a hypothesis by id."""
    week_key = week_key or get_current_week_key()
    data     = _load_ledger()
    for week in data["weeks"]:
        if week["week_key"] == week_key:
            before = len(week["hypotheses"])
            week["hypotheses"] = [h for h in week["hypotheses"] if h["id"] != hyp_id]
            if len(week["hypotheses"]) < before:
                _save_ledger(data)
                return True
    return False


def score_hypothesis(hyp_id: str, outcome_text: str, score: int,
                     model_predicted: bool, missed_signal: str,
                     week_key: str = None) -> bool:
    """File an outcome for a hypothesis during the Friday review."""
    week_key = week_key or get_current_week_key()
    data     = _load_ledger()
    for week in data["weeks"]:
        if week["week_key"] == week_key:
            for hyp in week["hypotheses"]:
                if hyp["id"] == hyp_id:
                    hyp["outcome"]         = outcome_text.strip()
                    hyp["score"]           = score
                    hyp["model_predicted"] = model_predicted
                    hyp["missed_signal"]   = missed_signal.strip()
                    hyp["scored_at"]       = str(datetime.now())
                    _recalculate_week_accuracy(week)
                    _save_ledger(data)
                    return True
    return False


def update_week_notes(notes: str, week_key: str = None) -> bool:
    week_key = week_key or get_current_week_key()
    data     = _load_ledger()
    for week in data["weeks"]:
        if week["week_key"] == week_key:
            week["notes"] = notes
            _save_ledger(data)
            return True
    return False


def _recalculate_week_accuracy(week: dict) -> None:
    """Recompute accuracy_pct for a week based on scored hypotheses."""
    scored = [h for h in week["hypotheses"] if h.get("score") is not None]
    if not scored:
        week["accuracy_pct"] = None
        week["scored"]       = False
        return
    total_possible = len(scored) * 2   # max score per hyp = 2
    total_earned   = sum(max(0, h["score"]) for h in scored)
    week["accuracy_pct"] = round(total_earned / total_possible * 100, 1) if total_possible else None
    week["scored"]       = all(h.get("score") is not None for h in week["hypotheses"])


# ─── Read helpers ─────────────────────────────────────────────────────────────

def get_all_weeks() -> list:
    """Return all weeks, newest first."""
    return _load_ledger().get("weeks", [])


def get_rolling_accuracy(n_weeks: int = 4) -> float | None:
    """Compute rolling N-week accuracy across all scored weeks."""
    weeks  = [w for w in get_all_weeks() if w.get("accuracy_pct") is not None]
    recent = weeks[:n_weeks]
    if not recent:
        return None
    return round(sum(w["accuracy_pct"] for w in recent) / len(recent), 1)


def get_accuracy_status(pct: float | None) -> str:
    if pct is None:
        return "pending"
    t = LEDGER_ACCURACY_THRESHOLDS
    if pct >= t["excellent"] * 100: return "excellent"
    if pct >= t["good"]      * 100: return "good"
    if pct >= t["review"]    * 100: return "review"
    return "rebuild"


def get_model_vs_manual_split() -> dict:
    """
    How often did the model signal predict the correct outcome?
    vs how often did your manual reasoning predict correctly?
    """
    model_correct  = 0
    model_total    = 0
    manual_correct = 0
    manual_total   = 0

    for week in get_all_weeks():
        for hyp in week.get("hypotheses", []):
            if hyp.get("score") is None:
                continue
            manual_total += 1
            if hyp["score"] > 0:
                manual_correct += 1
            if hyp.get("model_predicted") is not None:
                model_total += 1
                if hyp["model_predicted"] and hyp["score"] > 0:
                    model_correct += 1

    return {
        "model_accuracy":  round(model_correct  / model_total  * 100, 1) if model_total  else None,
        "manual_accuracy": round(manual_correct / manual_total * 100, 1) if manual_total else None,
        "model_total":     model_total,
        "manual_total":    manual_total,
    }
