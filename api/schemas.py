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
    fill_breadth: bool = True
    overwrite: bool = False


class WatchlistUpdateRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("symbols")
    @classmethod
    def strip_symbols(cls, values: list[str]) -> list[str]:
        return [str(v).strip() for v in values if str(v).strip()]


class PortfolioConfigUpdateRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class PortfolioBacktestRequest(BaseModel):
    symbols: Optional[list[str]] = None
    weight_mode: str = Field(default="equal", max_length=32)
    strategy: str = Field(default="default", max_length=64)
    horizon: int = Field(default=5, ge=1, le=60)
    test_size: float = Field(default=0.2, gt=0.0, lt=1.0)
    up_threshold: float = Field(default=0.02, ge=0.0, le=1.0)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    max_symbols: int = Field(default=10, ge=1, le=20)


class PaperAccountCreateRequest(BaseModel):
    initial_capital: Optional[float] = Field(default=None, gt=0.0, le=100_000_000.0)


class HoldingAdviceItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    quantity: int = Field(..., gt=0, le=100_000_000)
    available_quantity: Optional[int] = Field(default=None, ge=0, le=100_000_000)
    average_cost: float = Field(..., gt=0, le=100_000_000)

    @field_validator("symbol")
    @classmethod
    def strip_symbol(cls, value: str) -> str:
        return value.strip()


class HoldingAdviceRequest(BaseModel):
    holdings: list[HoldingAdviceItem] = Field(default_factory=list, max_length=50)


class CandidateResearchRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list, min_length=1, max_length=50)
    min_score: float = Field(default=0.60, ge=0.0, le=1.0)
    top_n: int = Field(default=10, ge=1, le=30)

    @field_validator("symbols")
    @classmethod
    def strip_candidate_symbols(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))


class TradingAgentsRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)

    @field_validator("symbol")
    @classmethod
    def strip_trading_agents_symbol(cls, value: str) -> str:
        return value.strip()


class ScreenerRunRequest(BaseModel):
    top_n: int = Field(default=5, ge=1, le=10)
    capital: float = Field(default=100_000.0, ge=1_000.0, le=100_000_000.0)
    min_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
