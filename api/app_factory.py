from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.common import ServiceError, error_response, normalize_validation_errors
from api.constants import ALLOWED_ORIGINS, APP_VERSION
from api.routes import admin, ai, auth, core, predictions, sentiment, stocks, system


def create_app() -> FastAPI:
    application = FastAPI(title="Stock Prediction System", version=APP_VERSION)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )

    @application.exception_handler(ServiceError)
    async def handle_service_error(_, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_response(exc.message, exc.data))

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                "Request validation failed",
                {"details": normalize_validation_errors(exc.errors())},
            ),
        )

    for module in (core, stocks, sentiment, ai, auth, admin, system, predictions):
        application.include_router(module.router)

    return application
