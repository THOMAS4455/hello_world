from __future__ import annotations

import time

from fastapi import APIRouter

from api.common import error_response, run_blocking, success_response, ServiceError
from api.schemas import AIRequest, ChatRequest
from api.services import ai_service

router = APIRouter(tags=["ai"])


async def _run_ai_query(query: str, query_type: str):
    t0 = time.monotonic()
    response = await run_blocking(ai_service.analyze, query, timeout=90.0)
    elapsed = round(time.monotonic() - t0, 3)
    return success_response(
        {
            "response": response,
            "response_time": elapsed,
            "query_type": query_type,
        }
    )


@router.post("/api/ai/quick-analyze")
async def quick_analyze(request: AIRequest):
    return await _run_ai_query(request.query, "quick_analysis")


@router.post("/api/ai/analyze")
async def deep_analyze(request: AIRequest):
    return await _run_ai_query(request.query, "deep_analysis")


@router.post("/api/ai/chat")
async def ai_chat(request: ChatRequest):
    try:
        t0 = time.monotonic()
        response = await run_blocking(ai_service.analyze, request.message, timeout=90.0)
        elapsed = round(time.monotonic() - t0, 3)
        return success_response(
            {
                "response": response,
                "response_time": elapsed,
            }
        )
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc), "AI service unavailable")
