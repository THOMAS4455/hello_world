from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
CACHE_PATH = DATA_DIR / "cache"
MODEL_PATH = DATA_DIR / "models"
DATABASE_PATH = DATA_DIR / "astocks_prediction.db"

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "127.0.0.1")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8768"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
