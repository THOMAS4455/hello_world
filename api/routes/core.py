import time

from fastapi import APIRouter

from api.constants import APP_VERSION

router = APIRouter(tags=["core"])


@router.get("/")
async def root():
    return {
        "message": "Stock prediction system is running",
        "version": APP_VERSION,
        "ai_service": "DeepSeek AI",
        "data_source": "AKShare",
    }


@router.get("/health")
async def health():
    return {"status": "healthy", "version": APP_VERSION, "timestamp": time.time()}
