from __future__ import annotations

import time

from fastapi import APIRouter

from api.common import run_blocking, success_response
from api.services import ai_service, data_service, prediction_service

router = APIRouter(tags=["system"])


@router.get("/api/system/health")
async def system_health():
    try:
        ai_status = await run_blocking(ai_service.get_service_status, timeout=10.0)
    except Exception as exc:
        ai_status = {"status": "offline", "error": str(exc)}

    try:
        ai_runtime = await run_blocking(ai_service.get_runtime_config, timeout=10.0)
    except Exception as exc:
        ai_runtime = {"error": str(exc)}

    try:
        data_runtime = await run_blocking(data_service.get_data_source_config, timeout=10.0)
    except Exception as exc:
        data_runtime = {"error": str(exc)}

    try:
        prediction_runtime = await run_blocking(prediction_service.get_model_info, timeout=10.0)
    except Exception as exc:
        prediction_runtime = {"status": "offline", "error": str(exc)}

    return success_response(
        {
            "status": "healthy",
            "service": "system",
            "timestamp": time.time(),
            "components": {
                "data_service": {
                    "status": "healthy" if "error" not in data_runtime else "offline",
                    "connected": "error" not in data_runtime,
                    "runtime": data_runtime,
                },
                "ai_service": ai_status,
                "prediction_service": {
                    "status": "healthy" if "error" not in prediction_runtime else "offline",
                    "connected": "error" not in prediction_runtime,
                    "runtime": prediction_runtime,
                },
            },
            "runtime": {
                "ai": ai_runtime,
                "data_source": data_runtime,
                "prediction": prediction_runtime,
            },
        }
    )
