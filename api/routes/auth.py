from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header

from api.common import ServiceError, error_response, extract_bearer_token, run_blocking, success_response
from api.schemas import LoginRequest, RefreshTokenRequest, RegisterRequest, UserProfileUpdateRequest, UserSettingsRequest
from api.services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/api/auth/register")
async def auth_register(request: RegisterRequest):
    try:
        user = await run_blocking(
            auth_service.register,
            request.username,
            request.email,
            request.password,
            timeout=15.0,
        )
        return success_response({"user": user}, "注册成功")
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/auth/login")
async def auth_login(request: LoginRequest):
    try:
        payload = await run_blocking(
            auth_service.login,
            request.username,
            request.password,
            timeout=15.0,
        )
        return success_response(payload, "登录成功")
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/auth/refresh")
async def auth_refresh(request: RefreshTokenRequest):
    try:
        payload = await run_blocking(
            auth_service.refresh_session,
            request.refresh_token,
            timeout=15.0,
        )
        return success_response(payload, "Session refreshed")
    except Exception as exc:
        return error_response(str(exc))


@router.post("/api/auth/logout")
async def auth_logout(authorization: Optional[str] = Header(default=None)):
    try:
        token = extract_bearer_token(authorization)
        await run_blocking(auth_service.logout, token, timeout=10.0)
        return success_response({}, "Logged out")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.get("/api/user/profile")
async def get_user_profile(authorization: Optional[str] = Header(default=None)):
    try:
        token = extract_bearer_token(authorization)
        user = await run_blocking(auth_service.validate_token, token, timeout=10.0)
        return success_response({"user": user})
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.put("/api/user/profile")
async def update_user_profile(
    request: UserProfileUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        token = extract_bearer_token(authorization)
        user = await run_blocking(
            auth_service.update_user_profile, token, request.profile, timeout=15.0
        )
        return success_response({"user": user}, "Profile updated")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))


@router.put("/api/user/settings")
async def update_user_settings(
    request: UserSettingsRequest,
    authorization: Optional[str] = Header(default=None),
):
    try:
        token = extract_bearer_token(authorization)
        user = await run_blocking(
            auth_service.update_user_settings, token, request.settings, timeout=15.0
        )
        return success_response({"user": user}, "设置已更新")
    except ServiceError:
        raise
    except Exception as exc:
        return error_response(str(exc))
