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

    def test_error_handling_integration(self, client):
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

        response = client.post("/health")
        assert response.status_code == 405

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
