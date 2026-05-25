from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from api.constants import ALLOWED_NEWS_SOURCES, DEFAULT_NEWS_SOURCES


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400, data: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.data = data or {}


def success_response(data: Any, message: Optional[str] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return payload


def error_response(message: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return {"success": False, "data": data or {}, "message": message}


def normalize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for error in errors:
        item = dict(error)
        ctx = item.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {key: str(value) for key, value in ctx.items()}
        normalized.append(item)
    return normalized


def extract_stock_list(stocks_response: Any) -> list[dict[str, Any]]:
    if isinstance(stocks_response, dict):
        return stocks_response.get("data", {}).get("stocks", [])
    if isinstance(stocks_response, list):
        return stocks_response
    return []


async def run_blocking(func: Callable[..., Any], *args: Any, timeout: float = 20.0) -> Any:
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(loop.run_in_executor(None, lambda: func(*args)), timeout=timeout)


def to_market_symbol(symbol: str) -> str:
    code = str(symbol or "").strip()
    if not code:
        return code
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    if code.startswith(("0", "3")):
        return f"sz{code}"
    if code.startswith(("4", "8", "9")):
        return f"bj{code}"
    return f"sz{code}"


def parse_sources(sources: Optional[str]) -> list[str]:
    parsed = [item.strip().lower() for item in (sources or "").split(",") if item.strip()]
    if not parsed:
        return list(DEFAULT_NEWS_SOURCES)
    invalid = [item for item in parsed if item not in ALLOWED_NEWS_SOURCES]
    if invalid:
        raise ServiceError(
            f"Unsupported news source: {', '.join(sorted(set(invalid)))}",
            status_code=422,
            data={"allowed_sources": sorted(ALLOWED_NEWS_SOURCES)},
        )
    return parsed


def extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise ServiceError("Missing Authorization header", status_code=401)
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ServiceError("Authorization header must use Bearer <token>", status_code=401)
    token = parts[1].strip()
    if not token:
        raise ServiceError("Bearer token cannot be empty", status_code=401)
    return token
