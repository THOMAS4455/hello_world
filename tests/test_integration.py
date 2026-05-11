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
        monkeypatch.setattr(app_module.data_service, "get_stocks", lambda: fake_stocks_payload)

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
