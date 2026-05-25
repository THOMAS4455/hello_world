#!/usr/bin/env python3
"""
Integration tests aligned with the current FastAPI backend.
External data/network calls are mocked to keep tests stable.
"""

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import app as app_module


class TestIntegration:
    @pytest.fixture
    def client(self):
        return TestClient(app_module.app)

    @pytest.fixture
    def isolated_auth_storage(self, tmp_path, monkeypatch):
        auth = app_module.auth_service
        users_file = tmp_path / "users.json"
        sessions_file = tmp_path / "sessions.json"
        monkeypatch.setattr(auth, "_users_file", users_file)
        monkeypatch.setattr(auth, "_sessions_file", sessions_file)
        auth._sessions = {}
        auth._refresh_index = {}
        return auth

    def test_api_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_stocks_data_health_endpoint(self, client, monkeypatch):
        monkeypatch.setattr(
            app_module.data_service,
            "get_data_health",
            lambda: {
                "live_only": True,
                "stock_source": "aggregate_realtime",
                "healthy_sources": 2,
                "total_sources": 3,
                "source_health": {"eastmoney_direct": {"success": True}},
            },
        )

        response = client.get("/api/stocks/data-health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["live_only"] is True
        assert payload["data"]["healthy_sources"] == 2

    def test_predict_post_with_body(self, client, monkeypatch):
        monkeypatch.setattr(
            app_module.prediction_service,
            "predict_stock",
            lambda symbol, horizon, up_threshold: {
                "symbol": symbol,
                "horizon": horizon,
                "up_threshold": up_threshold,
                "prediction": 1,
                "direction": "up",
                "confidence": 0.81,
            },
        )

        response = client.post(
            "/api/predictions/predict",
            json={"symbol": "000001", "horizon": 5, "up_threshold": 0.02},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["symbol"] == "000001"

    def test_stocks_api_endpoint(self, client, monkeypatch):
        fake_stocks_payload = {
            "success": True,
            "data": {
                "stocks": [
                    {
                        "symbol": "000001",
                        "name": "PingAn",
                        "price": 10.0,
                        "change": 0.1,
                        "change_percent": 1.0,
                    }
                ]
            },
        }
        monkeypatch.setattr(app_module.data_service, "get_stocks", lambda *args, **kwargs: fake_stocks_payload)

        response = client.get("/api/stocks")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "stocks" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] == 1

    def test_ai_chat_endpoint(self, client, monkeypatch):
        monkeypatch.setattr(app_module.ai_service, "analyze", lambda query: f"ok:{query}")

        response = client.post("/api/ai/chat", json={"message": "test"})
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "response" in data["data"]

    def test_user_profile_requires_bearer_token(self, client):
        response = client.get("/api/user/profile")
        assert response.status_code == 401

        data = response.json()
        assert data["success"] is False
        assert "Authorization" in data["message"]

    def test_news_sources_validation(self, client):
        response = client.get("/api/news/realtime?sources=invalid")
        assert response.status_code == 422

        data = response.json()
        assert data["success"] is False
        assert "allowed_sources" in data["data"]

    def test_register_request_validation(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "ab", "email": "bad-email", "password": "123"},
        )
        assert response.status_code == 422

        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Request validation failed"

    def test_error_handling_integration(self, client):
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

        response = client.post("/health")
        assert response.status_code == 405

    def test_auth_refresh_and_profile(self, client, isolated_auth_storage):
        register_response = client.post(
            "/api/auth/register",
            json={"username": "reviewer", "email": "reviewer@example.com", "password": "secret123"},
        )
        assert register_response.status_code == 200
        assert register_response.json()["success"] is True

        login_response = client.post(
            "/api/auth/login",
            json={"username": "reviewer", "password": "secret123"},
        )
        assert login_response.status_code == 200
        login_payload = login_response.json()["data"]
        assert login_payload["token"]
        assert login_payload["refreshToken"]

        profile_response = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {login_payload['token']}"},
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["data"]["user"]["username"] == "reviewer"

        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": login_payload["refreshToken"]},
        )
        assert refresh_response.status_code == 200
        refresh_payload = refresh_response.json()["data"]
        assert refresh_payload["token"] != login_payload["token"]
        assert refresh_payload["refreshToken"] != login_payload["refreshToken"]

        logout_response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {refresh_payload['token']}"},
        )
        assert logout_response.status_code == 200
        assert logout_response.json()["success"] is True

        expired_profile = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {refresh_payload['token']}"},
        )
        assert expired_profile.status_code == 200
        assert expired_profile.json()["success"] is False

    def test_profile_and_settings_update(self, client, isolated_auth_storage):
        client.post(
            "/api/auth/register",
            json={"username": "operator", "email": "operator@example.com", "password": "secret123"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"username": "operator", "password": "secret123"},
        )
        token = login_response.json()["data"]["token"]

        profile_response = client.put(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"profile": {"phone": "123456", "company": "OpenAI", "bio": "tester"}},
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["success"] is True
        assert profile_response.json()["data"]["user"]["profile"]["company"] == "OpenAI"

        settings_response = client.put(
            "/api/user/settings",
            headers={"Authorization": f"Bearer {token}"},
            json={"settings": {"theme": "dark", "language": "en-US"}},
        )
        assert settings_response.status_code == 200
        assert settings_response.json()["success"] is True
        assert settings_response.json()["data"]["user"]["settings"]["theme"] == "dark"

    def test_system_health_contains_runtime(self, client, monkeypatch):
        monkeypatch.setattr(app_module.ai_service, "get_service_status", lambda: {"status": "online", "model": "demo"})
        monkeypatch.setattr(app_module.ai_service, "get_runtime_config", lambda: {"model": "demo"})
        monkeypatch.setattr(
            app_module.data_service,
            "get_data_source_config",
            lambda: {"stock_source": "aggregate_realtime", "refresh_status": {"last_success_source": "direct_sina"}},
        )
        monkeypatch.setattr(
            app_module.prediction_service,
            "get_model_info",
            lambda: {"available_models": ["m1", "m2"], "model_status": "ready"},
        )

        response = client.get("/api/system/health")
        assert response.status_code == 200
        payload = response.json()["data"]
        assert "runtime" in payload
        assert payload["components"]["data_service"]["runtime"]["stock_source"] == "aggregate_realtime"
        assert payload["components"]["prediction_service"]["runtime"]["model_status"] == "ready"

    def test_prediction_history_endpoints(self, client, monkeypatch):
        monkeypatch.setattr(
            app_module.prediction_service,
            "predict_stock",
            lambda symbol, horizon, up_threshold: {
                "symbol": symbol,
                "horizon": horizon,
                "up_threshold": up_threshold,
                "prediction": 1,
                "direction": "up",
                "confidence": 0.81,
                "individual_predictions": {"m1": 1},
                "probabilities": {"m1": {"up": 0.81, "down": 0.19}},
                "model_scores": {},
                "layer_outputs": {},
                "explanation": "demo forecast",
                "timestamp": 123456.0,
            },
        )
        monkeypatch.setattr(
            app_module.prediction_service,
            "backtest_strategy",
            lambda symbol, strategy, horizon, test_size, up_threshold, min_confidence=0.0: {
                "symbol": symbol,
                "strategy": strategy,
                "horizon": horizon,
                "up_threshold": up_threshold,
                "min_confidence": min_confidence,
                "test_ratio": test_size,
                "period": "100 days",
                "results": {"walk_forward": {"accuracy": 0.61, "samples": 42}},
                "baseline_accuracy": 0.55,
                "improvement": 0.06,
                "feature_importance": {},
                "sentiment_comparison": {},
                "walk_forward": {"accuracy": 0.61, "samples": 42},
                "timestamp": 123457.0,
            },
        )
        monkeypatch.setattr(
            app_module.prediction_service,
            "get_prediction_history",
            lambda symbol=None, limit=20: [{"id": "pred-1", "symbol": "000001", "direction": "up", "confidence": 0.81}],
        )
        monkeypatch.setattr(
            app_module.prediction_service,
            "get_backtest_history",
            lambda symbol=None, limit=20: [{"id": "back-1", "symbol": "000001", "strategy": "default", "improvement": 0.06}],
        )
        monkeypatch.setattr(
            app_module.prediction_service,
            "get_prediction_run",
            lambda run_id: {"id": run_id, "result": {"symbol": "000001", "horizon": 5, "up_threshold": 0.02}},
        )
        monkeypatch.setattr(
            app_module.prediction_service,
            "get_backtest_run",
            lambda run_id: {"id": run_id, "result": {"symbol": "000001", "strategy": "default", "test_ratio": 0.2}},
        )

        predict_response = client.get("/api/predictions/predict", params={"symbol": "000001", "horizon": 5})
        assert predict_response.status_code == 200
        assert predict_response.json()["success"] is True

        history_response = client.get("/api/predictions/history", params={"symbol": "000001", "limit": 5})
        assert history_response.status_code == 200
        assert history_response.json()["success"] is True
        assert history_response.json()["data"]["items"][0]["symbol"] == "000001"
        assert history_response.json()["data"]["items"][0]["id"] == "pred-1"

        run_response = client.get("/api/predictions/history/pred-1")
        assert run_response.status_code == 200
        assert run_response.json()["success"] is True
        assert run_response.json()["data"]["item"]["result"]["symbol"] == "000001"

        backtest_response = client.post("/api/predictions/backtest", params={"symbol": "000001"})
        assert backtest_response.status_code == 200
        assert backtest_response.json()["success"] is True

        backtest_history_response = client.get("/api/predictions/backtest-history", params={"symbol": "000001", "limit": 5})
        assert backtest_history_response.status_code == 200
        assert backtest_history_response.json()["success"] is True
        assert backtest_history_response.json()["data"]["items"][0]["strategy"] == "default"
        assert backtest_history_response.json()["data"]["items"][0]["id"] == "back-1"

        backtest_run_response = client.get("/api/predictions/backtest-history/back-1")
        assert backtest_run_response.status_code == 200
        assert backtest_run_response.json()["success"] is True
        assert backtest_run_response.json()["data"]["item"]["result"]["strategy"] == "default"

    def test_admin_feature_history_endpoints(self, client, isolated_auth_storage, monkeypatch):
        monkeypatch.setattr(
            "api.routes.admin.feature_history_backfill_service.get_status",
            lambda: {
                "breadth_days": 2,
                "sentiment_days": 1,
                "breadth_range": {"start": "2024-01-01", "end": "2024-01-02"},
                "sentiment_range": {"start": "2024-01-01", "end": "2024-01-01"},
                "data_dir": "/tmp/feature_history",
            },
        )
        monkeypatch.setattr(
            "api.routes.admin.feature_history_backfill_service.run",
            lambda **kwargs: {
                "requested_days": kwargs.get("days", 90),
                "cutoff_date": "2024-01-01",
                "overwrite": kwargs.get("overwrite", False),
                "sentiment": {"enabled": True, "written": 1, "skipped": 0, "days": 1},
                "breadth": {"enabled": True, "written": 2, "skipped": 0, "days": 2, "source": "index_proxy"},
                "errors": [],
                "status": {"breadth_days": 2, "sentiment_days": 1},
            },
        )

        register_response = client.post(
            "/api/auth/register",
            json={"username": "admin", "email": "admin-feature@test.com", "password": "secret123"},
        )
        assert register_response.status_code == 200

        login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "secret123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        status_response = client.get("/api/admin/feature-history/status", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["success"] is True
        assert status_response.json()["data"]["breadth_days"] == 2

        backfill_response = client.post(
            "/api/admin/feature-history/backfill",
            headers=headers,
            json={
                "days": 30,
                "news_limit": 120,
                "fill_sentiment": True,
                "fill_breadth": True,
                "overwrite": False,
            },
        )
        assert backfill_response.status_code == 200
        assert backfill_response.json()["success"] is True
        assert backfill_response.json()["data"]["breadth"]["written"] == 2

        unauth_response = client.get("/api/admin/feature-history/status")
        assert unauth_response.status_code == 401

        client.post(
            "/api/auth/register",
            json={"username": "viewer99", "email": "viewer99@test.com", "password": "secret123"},
        )
        user_login = client.post(
            "/api/auth/login",
            json={"username": "viewer99", "password": "secret123"},
        )
        user_headers = {"Authorization": f"Bearer {user_login.json()['data']['token']}"}
        profile_response = client.get("/api/user/profile", headers=user_headers)
        assert profile_response.status_code == 200
        assert "admin" not in (profile_response.json()["data"]["user"].get("roles") or [])

        forbidden_response = client.get("/api/admin/feature-history/status", headers=user_headers)
        assert forbidden_response.status_code == 403
        assert forbidden_response.json()["success"] is False

    def test_cors_headers(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
