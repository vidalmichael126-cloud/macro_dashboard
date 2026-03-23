# Macro Signal Dashboard

A three-view macroeconomic signal dashboard built on the analytical framework
developed across our finance conversation. Tracks the Iran conflict / oil shock,
Asian market stress, US fiscal dynamics, and stagflation signals.

---

## The three views

| Tab | Purpose | When to use |
|-----|---------|-------------|
| Morning brief | 30-second regime check | Every morning before checking anything else |
| Signal board | Full signal grid with sparklines | When you want to understand what changed |
| Regime board | Scenario probabilities + action checklist | When making an actual investment decision |

---

## Quick start — local

```bash
# 1. Clone or download this folder
cd macro_dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Opens at http://localhost:8501

---

## Deploy to Streamlit Cloud (free, accessible from iPhone)

1. Push this folder to a GitHub repository (public or private)
2. Go to https://share.streamlit.io
3. Sign in with GitHub
4. Click "New app"
5. Select your repo, branch `main`, file `app.py`
6. Click Deploy

Your dashboard will have a permanent URL you can bookmark on your phone.
No server to maintain. Streamlit Cloud handles everything.

---

## File structure

```
macro_dashboard/
├── app.py              # Entry point — tab routing
├── config.py           # ALL thresholds, tickers, rules (edit this file)
├── data_feeds.py       # yfinance + FRED API calls with caching
├── signal_engine.py    # Signal status logic, combination rules, scenario scoring
├── views/
│   ├── morning_brief.py   # Dashboard C — default tab
│   ├── signal_board.py    # Dashboard B — depth view
│   └── regime_board.py    # Dashboard A — decision view
├── notebooks/
│   └── signal_development.ipynb  (add your Jupyter work here)
├── requirements.txt
└── .streamlit/config.toml
```

---

## The signal model

### Primary signals (Tier 1 — intraday)

| Signal | Ticker | Normal | Warning | Critical |
|--------|--------|--------|---------|----------|
| WTI crude oil | CL=F | < $90 | $120–150 | $150+ |
| VIX | ^VIX | < 20 | 30–40 | 40+ |
| 10yr yield | ^TNX | < 4.5% | 5.0–5.5% | 5.5%+ |
| USD/JPY | JPY=X | < 148 | 152–155 | 155+ |

### Combination rules

Rules fire when multiple signals cross thresholds simultaneously:

- **Sell America** — Oil elevated + yields rising + VIX elevated + dollar falling
- **XLE-oil divergence** — XLE falling while oil above $90 (early peace signal)
- **VIX capitulation** — VIX above 40 (historically marks S&P bottom ±6 weeks)
- **Carry trade unwind risk** — USD/JPY above 155
- **Stagflation confirmed** — Oil above $120 + yields rising

### Scenario scoring

The model starts with default probabilities (A=32%, B=47%, C=21%) and adjusts
based on current signal states. All adjustments are defined in `SCENARIO_SCORING_RULES`
in config.py — change them as your thesis evolves.

---

## Customizing the dashboard

Everything you need to change lives in `config.py`:

```python
# Change a threshold
THRESHOLDS["oil"]["warning"] = (130, 160)   # New warning zone

# Change default probabilities
SCENARIOS["A"]["probability_default"] = 40

# Add a new combination rule
COMBINATION_RULES.append({
    "name": "Your rule name",
    "description": "What it means",
    "action": "What to do",
    "severity": "warning",
    "conditions": {
        "oil": "elevated",
        "vix": "warning",
    },
})
```

The views automatically pick up any changes to config.py.

---

## Data sources

- **yfinance** — market prices (free, 15-min delayed, no API key needed)
- **FRED API** — macro data (free, no API key needed for CSV endpoint)
  - 10yr yield, 2yr yield, yield curve, CPI, unemployment, DXY

Data is cached: 15 minutes for intraday signals, 1 hour for macro data.

---

## Notebooks

Add your Jupyter analysis notebooks to the `notebooks/` folder.
They can import from `config.py`, `data_feeds.py`, and `signal_engine.py`
directly — shared logic, no duplication.

Example notebook workflow:
```python
import sys
sys.path.insert(0, '..')    # from notebooks/ folder, point to project root
from data_feeds import fetch_live_prices, fetch_sparklines
from signal_engine import get_full_analysis

analysis = get_full_analysis()
print(analysis["probs"])    # Current scenario probabilities
print(analysis["rules"])    # Active combination rules
```

---

## The intellectual framework

This dashboard operationalizes the macro model built across the conversation:

- **Oil shock → stagflation** (1973, 1979, 1990, 2008, 2022 historical analogs)
- **Asian transmission** (Japan/Korea oil dependence → Treasury selling → US yields)
- **Carry trade unwind** (USD/JPY above 155 → Bank of Japan intervention → US selloff)
- **XLE divergence signal** (Simons-style: energy stocks lead oil by 3–6 weeks)
- **PE liquidity crisis** (private credit stress visible via HYG spreads)
- **Bitcoin identity** (correlation with QQQ vs gold — which narrative is winning)

See the full conversation for the underlying logic behind each signal and threshold.

---

## When to update the model

- **Oil crosses a new threshold** → update scenario probabilities manually in config
- **Conflict resolves** → scenario A probability jumps, action rules flip
- **IEA holds second emergency meeting** → escalation signal, increase Scenario C weight
- **USD/JPY breaks 155** → add carry trade unwind as active rule manually

The model is a tool for disciplined thinking, not a black box.
Override it when you have thesis-level conviction. Trust it when you are emotional.
