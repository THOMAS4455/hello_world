from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header

from api.common import ServiceError, error_response, extract_bearer_token, run_blocking, success_response
from api.schemas import AdminSystemConfigUpdateRequest
from api.services import ai_service, auth_service, data_service, system_settings_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/users")
async def admin_list_users(authorization: Optional[str] = Header(default=None)):
    try:
        token = extract_bearer_token(authorization)
        payload = await run_blocking(auth_service.list_users, token, timeout=20.0)
        return success_response(payload)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/admin/database-info")
async def admin_database_info(authorization: Optional[str] = Header(default=None)):
    try:
        token = extract_bearer_token(authorization)
        payload = await run_blocking(auth_service.get_database_info, token, timeout=20.0)
        return success_response(payload)
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/admin/system-config")
async def admin_get_system_config(authorization: Optional[str] = Header(default=None)):
    try:
        token = extract_bearer_token(authorization)
        await run_blocking(auth_service.verify_admin, token, timeout=10.0)
        ai_config = await run_blocking(ai_service.get_runtime_config, timeout=10.0)
        data_source = await run_blocking(data_service.get_data_source_config, timeout=10.0)
        persisted = await run_blocking(system_settings_service.load, timeout=10.0)
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


@router.put("/api/admin/system-config")
async def admin_update_system_config(
    request: AdminSystemConfigUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        token = extract_bearer_token(authorization)
        await run_blocking(auth_service.verify_admin, token, timeout=10.0)

        ai_patch = request.ai if isinstance(request.ai, dict) else {}
        ds_patch = request.data_source if isinstance(request.data_source, dict) else {}

        await run_blocking(
            system_settings_service.update_settings,
            ai_service,
            data_service,
            ai_patch,
            ds_patch,
            timeout=30.0,
        )

        ai_config = await run_blocking(ai_service.get_runtime_config, timeout=10.0)
        data_source = await run_blocking(data_service.get_data_source_config, timeout=10.0)
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
