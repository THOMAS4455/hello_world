from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Query

from api.common import ServiceError, error_response, extract_stock_list, run_blocking, success_response, to_market_symbol
from api.services import data_service

router = APIRouter(tags=["stocks"])


def _build_history_from_sina(symbol: str, limit: int = 120) -> list[dict]:
    import akshare as ak

    market_symbol = to_market_symbol(symbol)
    df = ak.stock_zh_a_daily(symbol=market_symbol, adjust="qfq")
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


@router.get("/api/stocks/data-health")
async def get_stocks_data_health():
    try:
        payload = await run_blocking(data_service.get_data_health, timeout=10.0)
        return success_response(payload)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/stocks/trading-session")
async def get_trading_session():
    return success_response(data_service.get_trading_session_status())


@router.get("/api/stocks")
async def get_stocks(
    limit: int = Query(default=0, ge=0, le=5000),
    refresh: bool = Query(default=False),
):
    try:
        stocks_response = await run_blocking(data_service.get_stocks, limit, refresh, timeout=180.0)
    except asyncio.TimeoutError:
        return error_response("stock service timeout", {"stocks": [], "total": 0, "returned": 0})
    except ServiceError:
        raise
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

    stocks = extract_stock_list(stocks_response)
    return success_response({"stocks": stocks, "total": len(stocks), "returned": len(stocks)})


@router.get("/api/stocks/search")
async def search_stocks(
    q: str = Query(default="", max_length=128),
    limit: int = Query(default=20, ge=1, le=50),
):
    try:
        # Search filters cached market data; avoid full live refresh for responsiveness.
        stocks_response = await run_blocking(data_service.get_stocks, 0, False, timeout=90.0)
    except asyncio.TimeoutError:
        return error_response("stock service timeout", {"stocks": [], "total": 0})
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc), {"stocks": [], "total": 0})

    stocks = extract_stock_list(stocks_response)
    keyword = q.strip().lower()
    if keyword:
        filtered = [
            stock
            for stock in stocks
            if keyword in str(stock.get("symbol", "")).lower()
            or keyword in str(stock.get("name", "")).lower()
        ]
    else:
        filtered = stocks[:limit]

    return success_response({"stocks": filtered[:limit], "total": min(len(filtered), limit)})


@router.get("/api/stocks/realtime")
async def get_realtime_stocks():
    try:
        refresh = data_service.get_trading_session_status().get("should_auto_refresh", False)
        stocks_response = await run_blocking(data_service.get_stocks, 20, refresh, timeout=180.0)
    except asyncio.TimeoutError:
        return error_response("stock service timeout", {"timestamp": time.time(), "stocks": []})
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc), {"timestamp": time.time(), "stocks": []})

    if isinstance(stocks_response, dict) and "success" in stocks_response:
        data = stocks_response.get("data") or {}
        return success_response(
            {
                "timestamp": time.time(),
                "stocks": data.get("stocks", [])[:20],
                "freshness": data.get("freshness", {}),
                "last_update": data.get("last_update"),
            }
        )

    stocks = extract_stock_list(stocks_response)
    return success_response({"timestamp": time.time(), "stocks": stocks[:20]})


@router.get("/api/stocks/market-overview")
async def get_market_overview(refresh: bool = Query(default=True)):
    try:
        overview = await run_blocking(data_service.get_market_overview, refresh, timeout=180.0)
        return success_response(overview)
    except asyncio.TimeoutError:
        return error_response("market overview timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/stocks/{symbol}")
async def get_stock_detail(symbol: str):
    try:
        detail = await run_blocking(data_service.get_stock_detail, symbol, timeout=180.0)
        if not detail.get("history"):
            try:
                history = await run_blocking(_build_history_from_sina, symbol, 120, timeout=40.0)
                if history:
                    detail["history"] = history
            except Exception:
                pass
        return success_response(detail)
    except asyncio.TimeoutError:
        return error_response("stock detail timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))
