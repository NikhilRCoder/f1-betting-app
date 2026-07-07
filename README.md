# 🏎️ PitWall — F1 Betting Analytics Platform

**PitWall** is a professional, quantitative research platform for Formula One
betting markets. It models race outcomes, calculates probabilities, compares
them against bookmaker odds, detects value bets, and tracks profit & loss.

This is **not** a betting app — it is an analytics and decision-support tool.
The end goal is profit, and every architectural decision serves that objective.

---

## Architecture

Strict separation of concerns. Business logic lives in a core layer that knows
nothing about Streamlit, so the UI can later be swapped for React + FastAPI by
replacing only the `pages/` directory.

```
┌─────────────────────────────────────────┐
│          UI Layer (Streamlit)            │  pages/ + app.py
├─────────────────────────────────────────┤
│          Service Layer                   │  services/
├─────────────────────────────────────────┤
│  Models │ Analysis │ Scrapers │ Calcs    │  models/ analysis/ scrapers/ calculators/
├─────────────────────────────────────────┤
│         Data Access Layer                │  database/ (connection, repositories)
├─────────────────────────────────────────┤
│               SQLite                     │
└─────────────────────────────────────────┘
```

Supporting packages: `config/` (settings, logging), `visualizations/` (Plotly
theme + chart builders), `utilities/` (formatters, validators, helpers).

---

## Quick start

```bash
# Conda (preferred)
conda env create -f environment.yml
conda activate f1-analytics

# …or pip
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The database is created automatically on first launch at `data/pitwall.db`.

Run the tests with:

```bash
pytest
```

---

## Loading data

Historical data comes from **Ergast-style CSV dumps** — no live APIs. Place the
CSV files under `data/csv/` and seed the database:

```python
from pathlib import Path
from database.seed import seed_database

seed_database(Path("data/csv"))
```

Supported files: `drivers.csv`, `constructors.csv`, `circuits.csv`,
`races.csv`, `results.csv`, `qualifying.csv`, `pit_stops.csv`, `status.csv`.
Imports are idempotent (`INSERT OR REPLACE` on Ergast integer keys), so
re-running is safe.

---

## Build phases

The platform is built incrementally. Current status:

| Phase | Scope | Status |
|------|-------|--------|
| **1 — Foundation** | Structure, config, schema, connection, base repo, app shell, all pages | ✅ Delivered |
| **2 — Data Pipeline** | Repositories, CSV seeder, Settings import | ✅ Repos + seeder; ⏳ Settings upload |
| **3 — Analysis Engine** | Analysis modules, visualisations, analysis + dashboard pages | ✅ Delivered |
| **4 — Models & Betting Core** | Calculators, feature engineering, models, prediction/recommendation services, Playground/Model-Testing/Recommendations pages | ✅ Delivered |
| **5 — Odds, Scraping, Reports** | Odds service + page, upcoming-race integration, reports, bet tracker, Dashboard P&L | ✅ Delivered |

### What works today

- **Runnable Streamlit shell** with all 12 pages in the sidebar.
- **SQLite schema** auto-initialised on launch; **Settings** page shows live
  row counts per table.
- **Dashboard, Historical, Driver, Constructor and Circuit Analysis** pages —
  live over seeded data, with form charts, skill radars, head-to-heads,
  standings, circuit profiles and grid-importance stats.
- **Playground** page — fully interactive odds/EV/Kelly/arbitrage/dutching/
  overround/bankroll/risk-of-ruin calculators.
- **Analysis engine** (driver/constructor/circuit/qualifying/form) and the
  **service layer** (driver/constructor/circuit/race) with a themed Plotly
  chart/radar/heatmap toolkit.
- **Prediction models** — Elo, power ratings, Bayesian, Monte Carlo, logistic
  regression and XGBoost behind a shared `BaseModel` interface, combined by a
  weighted **ensemble** over a leak-free feature pipeline.
- **Recommendation engine** — compares model vs bookmaker probability to compute
  edge, EV, Kelly stake and a weighted 0-100 confidence score, then assigns a
  verdict (`STRONG_BET`/`SMALL_EDGE`/`NO_BET`/`AVOID`) with a written rationale.
- **Recommendations**, **Model Testing** (leak-free season backtest + calibration)
  and **Monte Carlo simulator** pages, all live.
- **Odds management** — scrape a URL or enter odds manually; drivers are matched
  by code/name, implied probability and market overround are computed.
- **Upcoming Race** integration — circuit profile, current odds, model view and
  value-highlighted recommendation cards on one page.
- **Reports** — CSV/Excel exports (recommendations, odds, predictions) and a
  pre-race PDF.
- **Bet tracker & Dashboard P&L** — log and settle bets; the Dashboard reports
  win rate, staked, P&L, ROI, a cumulative-P&L chart and performance by market.
- **Calculators**, **repositories**, **CSV seeder**, **feature engineering**,
  **models**, **analysis** and **services** (odds/bets/reports included) covered
  by `pytest` (61 passing).

---

## Pages

`01_dashboard` · `02_upcoming_race` · `03_historical` · `04_driver_analysis` ·
`05_constructor_analysis` · `06_circuit_analysis` · `07_odds` ·
`08_recommendations` · `09_playground` · `10_model_testing` · `11_reports` ·
`12_settings`

---

## Conventions

- Type hints and docstrings on every function; module-level docstrings everywhere.
- `logging`, never `print`. `pathlib.Path`, never string path concatenation.
- SQLite access only through context-managed connections / repositories.
- Calculators are pure functions — no side effects, no database access.
