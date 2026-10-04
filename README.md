# Stock Prediction System

This repository contains a local stock analysis and forecasting application with a FastAPI backend and a React frontend. The backend serves market data, prediction endpoints, authentication, user settings, and admin APIs. The frontend provides dashboards, stock detail views, prediction screens, an investment research hub, and account management.

The target data domain is the China A-share market and the broader Chinese market, so some Chinese text in upstream data, labels, or generated output is expected and cannot be fully avoided.

## 🎉 Latest Update: Algorithm Optimization (2025-01-28)

The prediction algorithm has been significantly enhanced:
- ✅ **90 features** (up from 25, +260%)
- ✅ **Up to 8 ML models** — sklearn ensemble by default; LightGBM, XGBoost, CatBoost when the optional deps are installed (up from 5, +60%)
- ✅ **Expected accuracy improvement**: 62-68% (from 58%, +4-10%)
- ✅ **Smart data preprocessing** with 88% data retention

**See**: 
- `docs/OPTIMIZATION_SUMMARY.md` - Quick overview
- `docs/USAGE_GUIDE.md` - Detailed usage guide
- `docs/OPTIMIZATION_COMPLETE.md` - Full technical report

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
- `GET /api/news/realtime`
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
- `GET /api/investment/paper/account`
- `POST /api/investment/paper/account`
- `GET /api/tasks/status`
- `POST /api/tasks/cancel`

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Frontend Notes

The frontend uses `REACT_APP_API_BASE_URL` when provided. If the variable is not set, it defaults to `http://localhost:8000`.

## Testing

Backend tests:

```bash
pytest tests
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
