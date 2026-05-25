from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastapi import APIRouter, Query

from api.common import ServiceError, error_response, parse_sources, run_blocking, success_response
from api.services import ai_service, market_sentiment_service

router = APIRouter(tags=["sentiment"])


@router.get("/api/sentiment/market")
async def get_market_sentiment(
    symbol: Optional[str] = Query(default=None, max_length=32),
    news_limit: int = Query(default=120, ge=1, le=400),
    keyword: Optional[str] = Query(default=None, max_length=128),
    sources: str = Query(default="sina,akshare"),
):
    try:
        source_list = parse_sources(sources)
        sentiment_data = await run_blocking(
            market_sentiment_service.build_market_sentiment,
            symbol.strip() if symbol else None,
            news_limit,
            keyword.strip() if keyword else None,
            source_list,
            timeout=90.0,
        )
        ai_summary = await run_blocking(ai_service.analyze, sentiment_data["ai_prompt"], timeout=90.0)
        sentiment_data["summary"] = ai_summary
        sentiment_data.pop("ai_prompt", None)
        return success_response(sentiment_data)
    except asyncio.TimeoutError:
        return error_response("market sentiment timeout")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/news/realtime")
async def get_realtime_finance_news(
    limit: int = Query(default=80, ge=1, le=400),
    keyword: Optional[str] = Query(default=None, max_length=128),
    sources: str = Query(default="sina,akshare"),
):
    try:
        source_list = parse_sources(sources)
        news_items = await run_blocking(
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
