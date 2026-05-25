from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Body, Query

from api.common import error_response, run_blocking, success_response
from api.schemas import BacktestRequest, PredictRequest
from api.services import prediction_service

router = APIRouter(tags=["predictions"])


async def _run_predict(symbol: str, horizon: int, up_threshold: float):
    return await run_blocking(
        prediction_service.predict_stock,
        symbol,
        horizon,
        up_threshold,
        timeout=180.0,
    )


async def _run_backtest(
    symbol: str,
    strategy: str,
    horizon: int,
    test_size: float,
    up_threshold: float,
    min_confidence: float = 0.0,
):
    return await run_blocking(
        prediction_service.backtest_strategy,
        symbol,
        strategy,
        horizon,
        test_size,
        up_threshold,
        min_confidence,
        timeout=300.0,
    )


@router.post("/api/predictions/predict")
async def predict_stock_post(request: PredictRequest):
    try:
        prediction = await _run_predict(request.symbol, request.horizon, request.up_threshold)
        return success_response(prediction)
    except asyncio.TimeoutError:
        return error_response("prediction timeout")
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/predictions/predict")
async def predict_stock_get(
    symbol: str = Query(..., min_length=1, max_length=32),
    horizon: int = Query(default=5, ge=1, le=60),
    up_threshold: float = Query(default=0.02, ge=0.0, le=1.0),
):
    try:
        prediction = await _run_predict(symbol, horizon, up_threshold)
        return success_response(prediction)
    except asyncio.TimeoutError:
        return error_response("prediction timeout")
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/predictions/backtest")
async def backtest_strategy_post(
    request: Optional[BacktestRequest] = Body(default=None),
    symbol: Optional[str] = Query(default=None, min_length=1, max_length=32),
    strategy: str = Query(default="default", max_length=64),
    horizon: int = Query(default=5, ge=1, le=60),
    test_size: float = Query(default=0.2, gt=0.0, lt=1.0),
    up_threshold: float = Query(default=0.02, ge=0.0, le=1.0),
):
    try:
        if request:
            result = await _run_backtest(
                request.symbol,
                request.strategy,
                request.horizon,
                request.test_size,
                request.up_threshold,
                request.min_confidence,
            )
        elif symbol:
            result = await _run_backtest(symbol, strategy, horizon, test_size, up_threshold, 0.0)
        else:
            return error_response("symbol is required")
        return success_response(result)
    except asyncio.TimeoutError:
        return error_response("backtest timeout")
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/predictions/backtest/query")
async def backtest_strategy_query(
    symbol: str = Query(..., min_length=1, max_length=32),
    strategy: str = Query(default="default", max_length=64),
    horizon: int = Query(default=5, ge=1, le=60),
    test_size: float = Query(default=0.2, gt=0.0, lt=1.0),
    up_threshold: float = Query(default=0.02, ge=0.0, le=1.0),
):
    """Legacy query-string backtest endpoint kept for compatibility."""
    try:
        result = await _run_backtest(symbol, strategy, horizon, test_size, up_threshold, 0.0)
        return success_response(result)
    except asyncio.TimeoutError:
        return error_response("backtest timeout")
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/predictions/history")
async def get_prediction_history(
    symbol: Optional[str] = Query(default=None, max_length=32),
    limit: int = Query(default=12, ge=1, le=100),
):
    try:
        rows = await run_blocking(
            prediction_service.get_prediction_history,
            symbol.strip() if symbol else None,
            limit,
            timeout=20.0,
        )
        return success_response({"items": rows, "count": len(rows), "symbol": symbol or "", "limit": limit})
    except Exception as exc:
        return error_response(str(exc), {"items": [], "count": 0, "symbol": symbol or "", "limit": limit})


@router.get("/api/predictions/history/{run_id}")
async def get_prediction_run(run_id: str):
    try:
        payload = await run_blocking(prediction_service.get_prediction_run, run_id, timeout=20.0)
        if not payload:
            return error_response("Prediction run not found", {"item": None})
        return success_response({"item": payload})
    except Exception as exc:
        return error_response(str(exc), {"item": None})


@router.get("/api/predictions/backtest-history")
async def get_backtest_history(
    symbol: Optional[str] = Query(default=None, max_length=32),
    limit: int = Query(default=12, ge=1, le=100),
):
    try:
        rows = await run_blocking(
            prediction_service.get_backtest_history,
            symbol.strip() if symbol else None,
            limit,
            timeout=20.0,
        )
        return success_response({"items": rows, "count": len(rows), "symbol": symbol or "", "limit": limit})
    except Exception as exc:
        return error_response(str(exc), {"items": [], "count": 0, "symbol": symbol or "", "limit": limit})


@router.get("/api/predictions/backtest-history/{run_id}")
async def get_backtest_run(run_id: str):
    try:
        payload = await run_blocking(prediction_service.get_backtest_run, run_id, timeout=20.0)
        if not payload:
            return error_response("Backtest run not found", {"item": None})
        return success_response({"item": payload})
    except Exception as exc:
        return error_response(str(exc), {"item": None})
