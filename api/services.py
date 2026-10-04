from __future__ import annotations

from flask_services.auth_service import auth_service
from flask_services.data_service import data_service
from flask_services.investment_service import investment_service
from flask_services.prediction_service import prediction_service
from flask_services.system_settings_service import system_settings_service
from services.real_ai_service import real_ai_service

ai_service = real_ai_service
system_settings_service.apply_runtime(ai_service, data_service)

__all__ = [
    "ai_service",
    "auth_service",
    "data_service",
    "investment_service",
    "prediction_service",
    "system_settings_service",
]
