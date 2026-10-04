# Stock Prediction System

**English** | [简体中文](README.md)

A local research and forecasting platform for the **China A-share market**: FastAPI backend plus a React frontend.
It ships a complete loop: data -> features -> prediction -> backtest -> screening -> risk control -> paper trading.

> **Positioning (limits first)**: this is a **research tool that can evaluate strategies honestly and control risk**.
> It is **not** a system that reliably makes money. No measurable, robust alpha has been found so far.
> See the **[capability report](docs/SYSTEM_CAPABILITY_REPORT.md)**.

## Measured status (2026-10-04)

Every number below comes from actually running the code in this repository, not from design intent.

| Item | Measured |
|---|---|
| Features produced by `prepare_features()` | **58** (22 base + 8 time-series + 13 cross + 15 microstructure) |
| Models trained by default | **5** (RandomForest / GradientBoosting / ExtraTrees / LogisticRegression / SVM); LightGBM, XGBoost and CatBoost join only when those optional packages are installed |
| Prediction edge over the majority-class baseline | **not demonstrated** - median `improvement` over all 34 stored backtests is **0.0000** (7/34 positive, max +1.89pp) |
| Why accuracy is misleading here | the label is `1 = 5-day return above +2%`, so 60-90% of samples are 0 and a constant "never up" predictor already scores 71% |
| Multi-symbol ablation (5 stocks / 1,767 out-of-sample rows) | best edge across every variant is only **+0.56pp**; the three-layer ensemble is negative on 3 of 5 symbols |

**Authoritative status report**: [docs/SYSTEM_CAPABILITY_REPORT.md](docs/SYSTEM_CAPABILITY_REPORT.md).

Historical write-ups claiming 79.93% accuracy / F1 0.7102 are **not reproducible**: the scripts behind them
import a non-existent `get_db_session` and silently fall back to `np.random.seed(42)` synthetic data.
Those documents now live under [docs/archive/](docs/archive/) with an invalidation notice.

## Measuring performance honestly

The metric of record is **edge = accuracy - majority-class baseline**, always reported together with the
sample size n and a Wilson interval. Below 200 resolved signals the report only says "insufficient sample"
and **no improvement may be claimed**.

```bash
# fetch bars -> settle matured signals -> rewrite the live report (idempotent)
python scripts/daily_live_validation.py

# ablation: compare variants on identical purged walk-forward folds (edge vs baseline)
python scripts/ablation_edge.py --all-symbols --folds 3

# dead-code audit (non-blocking in CI)
python scripts/audit_imports.py --report
```

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, FastAPI, Uvicorn |
| Data | AKShare (forward-adjusted daily bars), SQLite / JSON |
| Machine learning | scikit-learn; LightGBM / XGBoost (optional, graceful fallback) |
| Frontend | React 18, Redux Toolkit, React Router, Plotly |
| Scheduling | APScheduler (live validation on weekdays at 16:45) |

## Quick start

### 1. Backend

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux
.venv/Scripts/python app.py
```

The backend listens on `http://127.0.0.1:8000`; interactive docs are at `http://127.0.0.1:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm ci
npm start          # http://localhost:3000
```

The frontend reads `REACT_APP_API_BASE_URL` and defaults to `http://localhost:8000`.

### 3. Windows launchers

- `scripts/start_project.ps1` - starts backend and frontend in the background, logs under `logs/backend` and `logs/frontend`
- `scripts/start_bachelor_project.py`
- `start.bat`

### 4. Daily live validation (optional)

APScheduler triggers it while the server runs. To avoid depending on a running server, register a
Windows scheduled task (**run this yourself**):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1
```

## Repository layout

```text
.
|-- api/              HTTP routes
|-- flask_services/   service layer (legacy directory name; no Flask dependency)
|-- src/core/         predictor and data collection
|-- src/validation/   signal tracking, settlement, performance report, overfitting statistics
|-- src/trading/      trading constraints, paper account
|-- src/portfolio/    portfolio and risk engines
|-- src/research/     factors and screening decisions
|-- src/jobs/         scheduled jobs
|-- frontend/         React frontend
|-- scripts/          operations and evaluation scripts
|-- tests/            pytest suite
|-- docs/             documentation (including docs/archive/ for invalidated claims)
`-- data/             runtime data (never committed)
```

## Main endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | health check |
| GET | `/api/stocks` | stock list |
| GET | `/api/stocks/{symbol}` | stock detail |
| GET | `/api/stocks/realtime` | realtime quotes |
| GET | `/api/stocks/market-overview` | market overview |
| GET | `/api/predictions/predict` | single-stock direction prediction |
| POST | `/api/predictions/backtest` | backtest |
| POST | `/api/auth/register`, `/api/auth/login` | register / login |
| GET / PUT | `/api/investment/watchlist` | watchlist |
| POST | `/api/investment/portfolio/backtest` | portfolio backtest |
| **GET** | **`/api/investment/live-performance`** | **live performance (edge vs baseline plus sample verdict)** |
| GET / POST | `/api/investment/paper/account` | paper account |
| GET | `/api/tasks/status` | task status |

## Tests and CI

```bash
.venv/Scripts/python -m pytest tests -q          # 101 passed, 1 xfailed
cd frontend && npm ci && npm run build
```

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs three jobs on every push and pull request:
the full backend suite against pinned `requirements.txt`, the frontend `npm ci && npm run build`, and
a Python syntax compile plus dead-code audit.

## Known limitations (all unresolved)

1. **No robust alpha**: ML direction prediction, momentum factors and GBDT+Alpha158 all fail to beat the majority-class baseline (see the ablation table).
2. **Tiny live sample**: only 15 resolved signals so far, so the report is flagged `insufficient_n = true`.
3. **Survivorship bias**: only currently listed stocks are covered; delisted names are not merged in, so positive-return conclusions need a discount. See [docs/SURVIVORSHIP_BIAS.md](docs/SURVIVORSHIP_BIAS.md).
4. **Daily granularity**: no minute or order-book data, so no intraday work.
5. **Shorting is restricted in A-shares**: long-only, so long/short returns are not achievable.

## Security

- **Never commit credentials.** `docker-compose.yml` uses placeholders such as `${DEEPSEEK_API_KEY}`; real values belong in `.env`, which is git-ignored.
- `data/users.json` holds password hashes; `data/`, `logs/`, `.venv/` and `frontend/build/` are all excluded from version control.
- If a key ever reached git history, **rotate it**: scrubbing history does not make it safe again.

## Disclaimer

This project is for research and learning only. Nothing it outputs is investment advice.
