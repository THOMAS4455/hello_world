from __future__ import annotations

import json
import os

APP_VERSION = "3.1.0"
DEFAULT_NEWS_SOURCES = ["sina", "akshare"]
ALLOWED_NEWS_SOURCES = {"sina", "akshare"}

_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]


def _load_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return list(_DEFAULT_ORIGINS)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in raw.split(",") if item.strip()]


ALLOWED_ORIGINS = _load_allowed_origins() or list(_DEFAULT_ORIGINS)
