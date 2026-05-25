#!/usr/bin/env python3
"""Stock prediction backend entrypoint."""

from __future__ import annotations

import sys

import uvicorn

from api.app_factory import create_app
from api.services import (
    ai_service,
    auth_service,
    data_service,
    market_sentiment_service,
    prediction_service,
    system_settings_service,
)

app = create_app()

__all__ = [
    "app",
    "ai_service",
    "auth_service",
    "data_service",
    "market_sentiment_service",
    "prediction_service",
    "system_settings_service",
]

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("AI service initialized")
    print("Data service initialized")
    print("Prediction service initialized")
    print("Auth service initialized")
    print("Market sentiment service initialized")
    print("System settings service initialized")
    print("Starting stock prediction backend")
    print("URL: http://127.0.0.1:8000")
    print("Docs: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
