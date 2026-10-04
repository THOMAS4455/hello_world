# Stock Prediction System

This repository contains a local stock analysis and forecasting application with a FastAPI backend and a React frontend. The backend serves market data, prediction endpoints, authentication, user settings, and admin APIs. The frontend provides dashboards, stock detail views, prediction screens, an investment research hub, and account management.

The target data domain is the China A-share market and the broader Chinese market, so some Chinese text in upstream data, labels, or generated output is expected and cannot be fully avoided.

## Current status (measured 2026-10-04)

All numbers below were produced by running the code in this repository, not from design intent.

| Item | Measured |
|---|---|
| Features actually produced by `prepare_features()` | **58** (22 base + 8 time-series + 13 cross + 15 microstructure) |
| Models actually trained | **5** by default (RandomForest, GradientBoosting, ExtraTrees, LogisticRegression, SVM); LightGBM/XGBoost/CatBoost only when those optional packages are installed |
| Prediction edge over the majority-class baseline | **not demonstrated** — across all 34 stored backtests the median `improvement` is **0.0000** (7/34 positive, max +1.89pp) |
| Why accuracy is misleading here | the label is `1 = 5-day return above +2%`, so 60-90% of days are 0 and a constant "never up" predictor already scores 71% (median over stored backtests) |

**Authoritative status report**: [docs/SYSTEM_CAPABILITY_REPORT.md](docs/SYSTEM_CAPABILITY_REPORT.md).

Historical optimisation write-ups that claimed 79.93% accuracy / F1 0.7102 are **not reproducible**
(their data path imports a non-existent `get_db_session` and silently falls back to seeded synthetic data).
They now live under [docs/archive/](docs/archive/) with an invalidation notice.

### Measuring performance honestly

```bash
# settle matured signals from stored bars and rewrite the live report
python scripts/daily_live_validation.py

# compare variants on identical purged walk-forward folds (edge vs baseline)
python scripts/ablation_edge.py --symbol 000933 --folds 3
```

The metric of record is `edge = accuracy - majority_class_baseline`, reported with `n` and a Wilson
interval. Below 200 resolved signals the report is explicitly flagged `insufficient_n` and no
improvement may be claimed.

## Stack

- Python 3.9+
- FastAPI
- Uvicorn
- AKShare
- pandas
- NumPy
- scikit-learn
- **LightGBM, XGBoost, CatBoost** ⭐ (optional)
- TensorFlow (optional, LSTM model only)
- React 18
- Redux Toolkit
- React Router

## Repository Layout

```text
.
|-- app.py
|-- config/
|-- data/
|-- docs/
|-- flask_services/
|-- frontend/
|-- logs/
|-- scripts/
|-- services/
|-- src/
`-- tests/
```

## Requirements

- Python 3.9 or newer
- Node.js 16 or newer
- npm

## Install

Backend dependencies:

```bash
pip install -r requirements.txt
```

Frontend dependencies:

```bash
cd frontend
npm install
```

## Run Locally

From the project root:

```bash
py -3 app.py
```

The backend starts on `http://127.0.0.1:8000`.

In a second terminal:

```bash
cd frontend
npm start
```

The frontend starts on `http://localhost:3000`.

## Windows Startup Scripts

The repository includes helper scripts for local startup:

- `scripts/start_project.ps1`
- `scripts/start_bachelor_project.py`
- `start.bat`

The PowerShell launcher starts the backend and frontend in the background and writes logs under `logs/backend` and `logs/frontend`.

## Main Endpoints

- `GET /health`
- `GET /api/stocks`
- `GET /api/stocks/search`
- `GET /api/stocks/realtime`
- `GET /api/stocks/market-overview`
- `GET /api/stocks/{symbol}`
- `GET /api/predictions/predict`
- `POST /api/predictions/backtest`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/user/profile`
- `PUT /api/user/settings`
- `GET /api/admin/users`
- `GET /api/admin/database-info`
- `GET /api/admin/system-config`
- `PUT /api/admin/system-config`
- `GET /api/investment/watchlist`
- `PUT /api/investment/watchlist`
- `POST /api/investment/portfolio/backtest`
- `GET /api/investment/live-performance`
- `GET /api/investment/paper/account`
- `POST /api/investment/paper/account`
- `GET /api/tasks/status`
- `POST /api/tasks/cancel`

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Frontend Notes

The frontend uses `REACT_APP_API_BASE_URL` when provided. If the variable is not set, it defaults to `http://localhost:8000`.

## Testing

Backend tests (use the project virtualenv so versions match `requirements.txt`):

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
.venv/Scripts/python -m pytest tests -q
```

Frontend tests:

```bash
cd frontend
npm test
```

## Logs

Runtime logs are written to:

- `logs/backend`
- `logs/frontend`
- `logs/root_archive`

## Docker

Docker files are present in the repository, but the current local application entrypoint uses `app.py` on port `8000`. Review container settings before relying on the provided Docker configuration in development or production.

## Notes

- Market data is fetched through AKShare-backed services.
- Cached data is stored under `data/`.
- Model artifacts are stored under `data/models/`.
- Review runtime configuration files under `config/` before deployment.
