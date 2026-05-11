#!/usr/bin/env python3
"""
Stock prediction backend entrypoint.
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import Any, Callable, Optional

import uvicorn
from fastapi import FastAPI, Header, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

APP_VERSION = "3.1.0"
DEFAULT_NEWS_SOURCES = ["sina", "akshare"]
ALLOWED_NEWS_SOURCES = {"sina", "akshare"}

app = FastAPI(title="Stock Prediction System", version=APP_VERSION)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400, data: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.data = data or {}


class AIRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query cannot be empty")
        return value


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be empty")
        return value


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username", "email")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value:
            raise ValueError("invalid email address")
        return value.lower()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("username cannot be empty")
        return value


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=255)

    @field_validator("refresh_token")
    @classmethod
    def strip_refresh_token(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("refresh token cannot be empty")
        return value


class UserSettingsRequest(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


class AdminSystemConfigUpdateRequest(BaseModel):
    ai: Optional[dict[str, Any]] = None
    data_source: Optional[dict[str, Any]] = None


def success_response(data: Any, message: Optional[str] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return payload


def error_response(message: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return {"success": False, "data": data or {}, "message": message}


def _normalize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for error in errors:
        item = dict(error)
        ctx = item.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {key: str(value) for key, value in ctx.items()}
        normalized.append(item)
    return normalized


def _extract_stock_list(stocks_response: Any) -> list[dict[str, Any]]:
    if isinstance(stocks_response, dict):
        return stocks_response.get("data", {}).get("stocks", [])
    if isinstance(stocks_response, list):
        return stocks_response
    return []


async def _run_blocking(func: Callable[..., Any], *args: Any, timeout: float = 20.0) -> Any:
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(loop.run_in_executor(None, lambda: func(*args)), timeout=timeout)


def _to_market_symbol(symbol: str) -> str:
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


def _parse_sources(sources: Optional[str]) -> list[str]:
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


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise ServiceError("Missing Authorization header", status_code=401)
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ServiceError("Authorization header must use Bearer <token>", status_code=401)
    token = parts[1].strip()
    if not token:
        raise ServiceError("Bearer token cannot be empty", status_code=401)
    return token


def _build_history_from_sina(symbol: str, limit: int = 120) -> list[dict[str, Any]]:
    import akshare as ak

    market_symbol = _to_market_symbol(symbol)
    df = ak.stock_zh_a_daily(symbol=market_symbol, adjust="")
    if df is None or df.empty:
        return []

    rows = []
    for _, row in df.tail(limit).iterrows():
        date_value = row.get("date")
        if hasattr(date_value, "strftime"):
            date_text = date_value.strftime("%Y-%m-%d")
        else:
            date_text = str(date_value)
        rows.append(
            {
                "date": date_text,
                "open": float(row.get("open", 0) or 0),
                "high": float(row.get("high", 0) or 0),
                "low": float(row.get("low", 0) or 0),
                "close": float(row.get("close", 0) or 0),
                "volume": int(float(row.get("volume", 0) or 0)),
            }
        )
    return rows


allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

try:
    from services.real_ai_service import real_ai_service

    ai_service = real_ai_service
    print("AI service initialized")
except Exception as exc:
    print(f"AI service initialization failed: {exc}")
    raise

try:
    from flask_services.data_service import data_service

    print("Data service initialized")
except Exception as exc:
    print(f"Data service initialization failed: {exc}")
    raise

try:
    from flask_services.prediction_service import prediction_service

    print("Prediction service initialized")
except Exception as exc:
    print(f"Prediction service initialization failed: {exc}")
    raise

try:
    from flask_services.auth_service import auth_service

    print("Auth service initialized")
except Exception as exc:
    print(f"Auth service initialization failed: {exc}")
    raise

try:
    from flask_services.market_sentiment_service import MarketSentimentService

    market_sentiment_service = MarketSentimentService(data_service)
    print("Market sentiment service initialized")
except Exception as exc:
    print(f"Market sentiment service initialization failed: {exc}")
    raise

try:
    from flask_services.system_settings_service import system_settings_service

    system_settings_service.apply_runtime(ai_service, data_service)
    print("System settings service initialized")
except Exception as exc:
    print(f"System settings service initialization failed: {exc}")
    raise


@app.exception_handler(ServiceError)
async def handle_service_error(_, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.message, exc.data))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_response(
            "Request validation failed",
            {"details": _normalize_validation_errors(exc.errors())},
        ),
    )


@app.get("/")
async def root():
    return {
        "message": "Stock prediction system is running",
        "version": APP_VERSION,
        "ai_service": "DeepSeek AI",
        "data_source": "AKShare",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": APP_VERSION, "timestamp": time.time()}


@app.get("/api/stocks")
async def get_stocks(
    limit: int = Query(default=0, ge=0, le=5000),
    refresh: bool = Query(default=False),
):
    try:
        try:
            stocks_response = await _run_blocking(
                data_service.get_stocks, limit, refresh, timeout=180.0
            )
        except TypeError:
            try:
                stocks_response = await _run_blocking(data_service.get_stocks, limit, timeout=180.0)
            except TypeError:
                stocks_response = await _run_blocking(data_service.get_stocks, timeout=180.0)
    except asyncio.TimeoutError:
        return error_response("stock service timeout", {"stocks": [], "total": 0, "returned": 0})
    except Exception as exc:
        return error_response(str(exc), {"stocks": [], "total": 0, "returned": 0})

    if isinstance(stocks_response, dict) and "success" in stocks_response:
        data = stocks_response.get("data") or {}
        stocks = data.get("stocks") or []
        if "total" not in data:
            data["total"] = len(stocks)
        if "returned" not in data:
            data["returned"] = len(stocks)
        stocks_response["data"] = data
        return stocks_response

    stocks = _extract_stock_list(stocks_response)
    return success_response({"stocks": stocks, "total": len(stocks), "returned": len(stocks)})


@app.get("/api/stocks/search")
async def search_stocks(q: str = Query(default="", max_length=128)):
    try:
        stocks_response = await _run_blocking(data_service.get_stocks, timeout=180.0)
    except asyncio.TimeoutError:
        return error_response("stock service timeout", {"stocks": [], "total": 0})
    except Exception as exc:
        return error_response(str(exc), {"stocks": [], "total": 0})

    stocks = _extract_stock_list(stocks_response)
    keyword = q.strip().lower()
    if keyword:
        filtered = [
            stock
            for stock in stocks
            if keyword in str(stock.get("symbol", "")).lower()
            or keyword in str(stock.get("name", "")).lower()
        ]
    else:
        filtered = stocks[:10]

    return success_response({"stocks": filtered, "total": len(filtered)})


@app.get("/api/stocks/realtime")
async def get_realtime_stocks():
    try:
        stocks_response = await _run_blocking(data_service.get_stocks, timeout=180.0)
    except asyncio.TimeoutError:
        return error_response("stock service timeout", {"timestamp": time.time(), "stocks": []})
    except Exception as exc:
        return error_response(str(exc), {"timestamp": time.time(), "stocks": []})

    stocks = _extract_stock_list(stocks_response)
    return success_response({"timestamp": time.time(), "stocks": stocks[:20]})


@app.get("/api/stocks/market-overview")
async def get_market_overview(refresh: bool = Query(default=False)):
    try:
        overview = await _run_blocking(data_service.get_market_overview, refresh, timeout=20.0)
        return success_response(overview)
    except asyncio.TimeoutError:
        return error_response("market overview timeout")
    except Exception as exc:
        return error_response(str(exc))


@app.get("/api/sentiment/market")
async def get_market_sentiment(
    symbol: Optional[str] = Query(default=None, max_length=32),
    news_limit: int = Query(default=120, ge=1, le=400),
    keyword: Optional[str] = Query(default=None, max_length=128),
    sources: str = Query(default="sina,akshare"),
):
    try:
        source_list = _parse_sources(sources)
        sentiment_data = await _run_blocking(
            market_sentiment_service.build_market_sentiment,
            symbol.strip() if symbol else None,
            news_limit,
            keyword.strip() if keyword else None,
            source_list,
            timeout=90.0,
        )
        ai_summary = await _run_blocking(ai_service.analyze, sentiment_data["ai_prompt"], timeout=90.0)
        sentiment_data["summary"] = ai_summary
        sentiment_data.pop("ai_prompt", None)
        return success_response(sentiment_data)
    except asyncio.TimeoutError:
        return error_response("market sentiment timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.get("/api/news/realtime")
async def get_realtime_finance_news(
    limit: int = Query(default=80, ge=1, le=400),
    keyword: Optional[str] = Query(default=None, max_length=128),
    sources: str = Query(default="sina,akshare"),
):
    try:
        source_list = _parse_sources(sources)
        news_items = await _run_blocking(
            market_sentiment_service._fetch_finance_news,
            limit,
            source_list,
            timeout=90.0,
        )

        keyword_text = (keyword or "").strip().lower()
        if keyword_text:
            news_items = [
                item for item in news_items if keyword_text in str(item.get("title", "")).lower()
            ]

        return success_response(
            {
                "items": news_items,
                "count": len(news_items),
                "limit": limit,
                "keyword": keyword or "",
                "sources": source_list,
                "timestamp": time.time(),
            }
        )
    except asyncio.TimeoutError:
        return error_response("news service timeout", {"items": [], "count": 0})
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc), {"items": [], "count": 0})


@app.get("/api/stocks/{symbol}")
async def get_stock_detail(symbol: str):
    try:
        detail = await _run_blocking(data_service.get_stock_detail, symbol, timeout=180.0)
        if not detail.get("history"):
            try:
                history = await _run_blocking(_build_history_from_sina, symbol, 120, timeout=40.0)
                if history:
                    detail["history"] = history
            except Exception:
                pass
        return success_response(detail)
    except asyncio.TimeoutError:
        return error_response("stock detail timeout")
    except Exception as exc:
        return error_response(str(exc))


async def _run_ai_query(query: str, response_time: float, query_type: str):
    response = await _run_blocking(ai_service.analyze, query, timeout=90.0)
    return success_response(
        {
            "response": response,
            "response_time": response_time,
            "query_type": query_type,
        }
    )


@app.post("/api/ai/quick-analyze")
async def quick_analyze(request: AIRequest):
    return await _run_ai_query(request.query, 0.5, "quick_analysis")


@app.post("/api/ai/analyze")
async def deep_analyze(request: AIRequest):
    return await _run_ai_query(request.query, 1.2, "deep_analysis")


@app.post("/api/ai/chat")
async def ai_chat(request: ChatRequest):
    try:
        response = await _run_blocking(ai_service.analyze, request.message, timeout=90.0)
        return success_response(
            {
                "response": response,
                "confidence": 0.85,
                "sentiment": "neutral",
            }
        )
    except Exception as exc:
        return {"success": False, "error": str(exc), "message": "AI service unavailable"}


@app.post("/api/auth/register")
async def auth_register(request: RegisterRequest):
    try:
        user = await _run_blocking(
            auth_service.register,
            request.username,
            request.email,
            request.password,
            timeout=15.0,
        )
        return success_response({"user": user}, "注册成功")
    except Exception as exc:
        return error_response(str(exc))


@app.post("/api/auth/login")
async def auth_login(request: LoginRequest):
    try:
        payload = await _run_blocking(
            auth_service.login,
            request.username,
            request.password,
            timeout=15.0,
        )
        return success_response(payload, "登录成功")
    except Exception as exc:
        return error_response(str(exc))


@app.post("/api/auth/refresh")
async def auth_refresh(request: RefreshTokenRequest):
    try:
        payload = await _run_blocking(
            auth_service.refresh_session,
            request.refresh_token,
            timeout=15.0,
        )
        return success_response(payload, "Session refreshed")
    except Exception as exc:
        return error_response(str(exc))


@app.post("/api/auth/logout")
async def auth_logout(authorization: Optional[str] = Header(default=None)):
    try:
        token = _extract_bearer_token(authorization)
        await _run_blocking(auth_service.logout, token, timeout=10.0)
        return success_response({}, "Logged out")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.get("/api/user/profile")
async def get_user_profile(authorization: Optional[str] = Header(default=None)):
    try:
        token = _extract_bearer_token(authorization)
        user = await _run_blocking(auth_service.validate_token, token, timeout=10.0)
        return success_response({"user": user})
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.put("/api/user/settings")
async def update_user_settings(
    request: UserSettingsRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        token = _extract_bearer_token(authorization)
        user = await _run_blocking(
            auth_service.update_user_settings, token, request.settings, timeout=15.0
        )
        return success_response({"user": user}, "设置已更新")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.get("/api/admin/users")
async def admin_list_users(authorization: Optional[str] = Header(default=None)):
    try:
        token = _extract_bearer_token(authorization)
        payload = await _run_blocking(auth_service.list_users, token, timeout=20.0)
        return success_response(payload)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.get("/api/admin/database-info")
async def admin_database_info(authorization: Optional[str] = Header(default=None)):
    try:
        token = _extract_bearer_token(authorization)
        payload = await _run_blocking(auth_service.get_database_info, token, timeout=20.0)
        return success_response(payload)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.get("/api/admin/system-config")
async def admin_get_system_config(authorization: Optional[str] = Header(default=None)):
    try:
        token = _extract_bearer_token(authorization)
        await _run_blocking(auth_service.verify_admin, token, timeout=10.0)
        ai_config = await _run_blocking(ai_service.get_runtime_config, timeout=10.0)
        data_source = await _run_blocking(data_service.get_data_source_config, timeout=10.0)
        persisted = await _run_blocking(system_settings_service.load, timeout=10.0)
        return success_response(
            {
                "ai": ai_config,
                "data_source": data_source,
                "persisted": persisted,
            }
        )
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.put("/api/admin/system-config")
async def admin_update_system_config(
    request: AdminSystemConfigUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        token = _extract_bearer_token(authorization)
        await _run_blocking(auth_service.verify_admin, token, timeout=10.0)

        ai_patch = request.ai if isinstance(request.ai, dict) else {}
        ds_patch = request.data_source if isinstance(request.data_source, dict) else {}

        await _run_blocking(
            system_settings_service.update_settings,
            ai_service,
            data_service,
            ai_patch,
            ds_patch,
            timeout=30.0,
        )

        ai_config = await _run_blocking(ai_service.get_runtime_config, timeout=10.0)
        data_source = await _run_blocking(data_service.get_data_source_config, timeout=10.0)
        return success_response(
            {
                "ai": ai_config,
                "data_source": data_source,
            },
            "系统配置更新成功",
        )
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@app.get("/api/system/health")
async def system_health():
    try:
        ai_status = await _run_blocking(ai_service.get_service_status, timeout=10.0)
    except Exception as exc:
        ai_status = {"status": "offline", "error": str(exc)}

    return success_response(
        {
            "status": "healthy",
            "service": "system",
            "timestamp": time.time(),
            "components": {
                "data_service": {"status": "healthy", "connected": True},
                "ai_service": ai_status,
                "prediction_service": {"status": "healthy", "connected": True},
            },
        }
    )


@app.get("/api/predictions/predict")
async def predict_stock(
    symbol: str = Query(..., min_length=1, max_length=32),
    horizon: int = Query(default=5, ge=1, le=60),
    up_threshold: float = Query(default=0.02, ge=0.0, le=1.0),
):
    try:
        prediction = await _run_blocking(
            prediction_service.predict_stock,
            symbol,
            horizon,
            up_threshold,
            timeout=60.0,
        )
        return success_response(prediction)
    except asyncio.TimeoutError:
        return error_response("prediction timeout")
    except Exception as exc:
        return error_response(str(exc))


@app.post("/api/predictions/backtest")
async def backtest_strategy(
    symbol: str = Query(..., min_length=1, max_length=32),
    strategy: str = Query(default="default", max_length=64),
    horizon: int = Query(default=5, ge=1, le=60),
    test_size: float = Query(default=0.2, gt=0.0, lt=1.0),
    up_threshold: float = Query(default=0.02, ge=0.0, le=1.0),
):
    try:
        result = await _run_blocking(
            prediction_service.backtest_strategy,
            symbol,
            strategy,
            horizon,
            test_size,
            up_threshold,
            timeout=150.0,
        )
        return success_response(result)
    except asyncio.TimeoutError:
        return error_response("backtest timeout")
    except Exception as exc:
        return error_response(str(exc))


if __name__ == "__main__":
    print("Starting stock prediction backend")
    print("URL: http://127.0.0.1:8000")
    print("Docs: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
