from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Header, Query

from api.common import ServiceError, error_response, extract_bearer_token, run_blocking, success_response
from api.schemas import (
    PaperAccountCreateRequest,
    PortfolioBacktestRequest,
    PortfolioConfigUpdateRequest,
    HoldingAdviceRequest,
    CandidateResearchRequest,
    ScreenerRunRequest,
    TradingAgentsRequest,
    WatchlistUpdateRequest,
)
from api.services import auth_service, investment_service

router = APIRouter(tags=["investment"])


async def _require_user_id(authorization: Optional[str]) -> int:
    token = extract_bearer_token(authorization)
    user = await run_blocking(auth_service.validate_token, token, timeout=10.0)
    user_id = user.get("id")
    if user_id is None:
        raise ServiceError("Invalid user session", status_code=401)
    return int(user_id)


@router.get("/api/investment/watchlist")
async def get_watchlist(authorization: Optional[str] = Header(default=None)):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(investment_service.get_watchlist, user_id, timeout=15.0)
        return success_response(data)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.put("/api/investment/watchlist")
async def update_watchlist(
    request: WatchlistUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.update_watchlist, user_id, request.symbols, timeout=15.0
        )
        return success_response(data, "Watchlist updated")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/config")
async def get_portfolio_config(authorization: Optional[str] = Header(default=None)):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(investment_service.get_portfolio_config, user_id, timeout=15.0)
        return success_response(data)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.put("/api/investment/config")
async def update_portfolio_config(
    request: PortfolioConfigUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.update_portfolio_config, user_id, request.config, timeout=15.0
        )
        return success_response(data, "Portfolio config updated")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/investment/portfolio/backtest")
async def portfolio_backtest(
    request: PortfolioBacktestRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.run_portfolio_backtest,
            user_id,
            request.symbols,
            weight_mode=request.weight_mode,
            horizon=request.horizon,
            test_size=request.test_size,
            up_threshold=request.up_threshold,
            min_confidence=request.min_confidence,
            strategy=request.strategy,
            max_symbols=request.max_symbols,
            timeout=300.0,
        )
        return success_response(data)
    except asyncio.TimeoutError:
        return error_response("portfolio backtest timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/paper/account")
async def get_paper_account(authorization: Optional[str] = Header(default=None)):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(investment_service.get_paper_account, user_id, timeout=15.0)
        return success_response({"account": data})
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/investment/paper/account")
async def create_paper_account(
    request: PaperAccountCreateRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.create_paper_account,
            user_id,
            request.initial_capital,
            timeout=15.0,
        )
        return success_response({"account": data}, "Paper account created")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/investment/paper/advance-day")
async def advance_paper_day(authorization: Optional[str] = Header(default=None)):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(investment_service.advance_paper_day, user_id, timeout=180.0)
        return success_response(data)
    except asyncio.TimeoutError:
        return error_response("paper advance timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/paper/equity-curve")
async def get_paper_equity_curve(authorization: Optional[str] = Header(default=None)):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(investment_service.get_paper_equity_curve, user_id, timeout=15.0)
        return success_response(data)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/paper/trades")
async def get_paper_trades(
    authorization: Optional[str] = Header(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        user_id = await _require_user_id(authorization)
        rows = await run_blocking(investment_service.get_paper_trades, user_id, limit, timeout=15.0)
        return success_response({"items": rows, "count": len(rows)})
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/signal-stats/{symbol}")
async def get_signal_stats(
    symbol: str,
    authorization: Optional[str] = Header(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.get_signal_stats,
            symbol.strip(),
            limit,
            None,
            timeout=15.0,
        )
        return success_response(data)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/portfolio/report/{cache_key:path}")
async def get_portfolio_report(
    cache_key: str,
    authorization: Optional[str] = Header(default=None),
):
    try:
        await _require_user_id(authorization)
        data = await run_blocking(investment_service.get_portfolio_report, cache_key, timeout=15.0)
        if not data:
            raise ServiceError("Report not found or expired", status_code=404)
        return success_response(data)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/live-performance")
async def get_live_performance(min_samples: int = Query(default=200, ge=1, le=100000)):
    """Rolling live-validation metrics for the recorded prediction signals.

    Read-only and network-free: computed from data/signal_logs.json.
    """
    try:
        data = await run_blocking(
            investment_service.get_live_performance, min_samples, timeout=15.0
        )
        return success_response(data)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/daily-brief")
async def get_daily_brief(authorization: Optional[str] = Header(default=None)):
    try:
        user_id = await _require_user_id(authorization)
        data = await run_blocking(investment_service.get_daily_brief, user_id, timeout=180.0)
        return success_response(data)
    except asyncio.TimeoutError:
        return error_response("daily brief timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/investment/holdings/advice")
async def get_holding_advice(
    request: HoldingAdviceRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.get_holding_advice,
            [item.model_dump() for item in request.holdings],
            timeout=300.0,
        )
        return success_response(data)
    except asyncio.TimeoutError:
        return error_response("holding advice timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/investment/research/candidates")
async def run_candidate_research(
    request: CandidateResearchRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.run_candidate_research,
            request.symbols,
            request.min_score,
            request.top_n,
            timeout=300.0,
        )
        return success_response(data)
    except asyncio.TimeoutError:
        return error_response("candidate research timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/investment/trading-agents/review")
async def run_trading_agents_review(request: TradingAgentsRequest, authorization: Optional[str] = Header(default=None)):
    try:
        await _require_user_id(authorization)
        data = await run_blocking(investment_service.run_trading_agents_review, request.symbol, timeout=300.0)
        return success_response(data)
    except asyncio.TimeoutError:
        return error_response("TradingAgents review timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/investment/screener/run")
async def run_daily_screener(request: ScreenerRunRequest, authorization: Optional[str] = Header(default=None)):
    try:
        await _require_user_id(authorization)
        data = await run_blocking(
            investment_service.run_daily_screener,
            request.top_n,
            request.capital,
            request.min_confidence,
            timeout=600.0,
        )
        return success_response(data)
    except asyncio.TimeoutError:
        return error_response("screener timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/investment/screener/latest")
async def get_latest_daily_picks(authorization: Optional[str] = Header(default=None)):
    try:
        await _require_user_id(authorization)
        data = await run_blocking(investment_service.get_daily_picks, timeout=15.0)
        if not data:
            raise ServiceError("No daily picks available yet", status_code=404)
        return success_response(data)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))
