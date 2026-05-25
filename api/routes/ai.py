from __future__ import annotations

from fastapi import APIRouter

from api.common import error_response, run_blocking, success_response
from api.schemas import AIRequest, ChatRequest
from api.services import ai_service

router = APIRouter(tags=["ai"])


async def _run_ai_query(query: str, response_time: float, query_type: str):
    response = await run_blocking(ai_service.analyze, query, timeout=90.0)
    return success_response(
        {
            "response": response,
            "response_time": response_time,
            "query_type": query_type,
        }
    )


@router.post("/api/ai/quick-analyze")
async def quick_analyze(request: AIRequest):
    return await _run_ai_query(request.query, 0.5, "quick_analysis")


@router.post("/api/ai/analyze")
async def deep_analyze(request: AIRequest):
    return await _run_ai_query(request.query, 1.2, "deep_analysis")


@router.post("/api/ai/chat")
async def ai_chat(request: ChatRequest):
    try:
        response = await run_blocking(ai_service.analyze, request.message, timeout=90.0)
        return success_response(
            {
                "response": response,
                "confidence": 0.85,
                "sentiment": "neutral",
            }
        )
    except Exception as exc:
        return {"success": False, "error": str(exc), "message": "AI service unavailable"}
