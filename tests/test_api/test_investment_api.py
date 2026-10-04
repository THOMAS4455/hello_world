"""API tests for investment endpoints."""

import pytest


def _register_and_login(client, username="invuser", email="inv@example.com", password="secret12"):
    client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    data = resp.json()
    assert data.get("success") is True
    token = data["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_investment_watchlist_requires_auth(client):
    resp = client.get("/api/investment/watchlist")
    assert resp.status_code == 401


def test_investment_watchlist_flow(client, isolated_auth_storage, isolated_investment_storage):
    headers = _register_and_login(client, username="invuser2", email="inv2@example.com")
    resp = client.get("/api/investment/watchlist", headers=headers)
    assert resp.json()["success"] is True
    assert resp.json()["data"]["symbols"] == []

    resp = client.put(
        "/api/investment/watchlist",
        headers=headers,
        json={"symbols": ["000001", "600000"]},
    )
    assert resp.json()["success"] is True
    assert resp.json()["data"]["symbols"] == ["000001", "600000"]


def test_signal_stats_auth(client, isolated_auth_storage, isolated_investment_storage):
    headers = _register_and_login(client, username="invuser3", email="inv3@example.com")
    resp = client.get("/api/investment/signal-stats/000001", headers=headers)
    assert resp.json()["success"] is True
    assert "samples" in resp.json()["data"]
