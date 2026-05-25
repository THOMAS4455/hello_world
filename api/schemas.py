from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class AIRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query cannot be empty")
        return value


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be empty")
        return value


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username", "email")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value:
            raise ValueError("invalid email address")
        return value.lower()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("username cannot be empty")
        return value


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=255)

    @field_validator("refresh_token")
    @classmethod
    def strip_refresh_token(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("refresh token cannot be empty")
        return value


class UserSettingsRequest(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


class UserProfileUpdateRequest(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)


class AdminSystemConfigUpdateRequest(BaseModel):
    ai: Optional[dict[str, Any]] = None
    data_source: Optional[dict[str, Any]] = None


class PredictRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    horizon: int = Field(default=5, ge=1, le=60)
    up_threshold: float = Field(default=0.02, ge=0.0, le=1.0)

    @field_validator("symbol")
    @classmethod
    def strip_symbol(cls, value: str) -> str:
        return value.strip()


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    strategy: str = Field(default="default", max_length=64)
    horizon: int = Field(default=5, ge=1, le=60)
    test_size: float = Field(default=0.2, gt=0.0, lt=1.0)
    up_threshold: float = Field(default=0.02, ge=0.0, le=1.0)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("symbol")
    @classmethod
    def strip_symbol(cls, value: str) -> str:
        return value.strip()


class FeatureHistoryBackfillRequest(BaseModel):
    days: int = Field(default=90, ge=7, le=365)
    news_limit: int = Field(default=300, ge=50, le=500)
    fill_sentiment: bool = True
    fill_breadth: bool = True
    overwrite: bool = False
