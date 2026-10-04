#!/usr/bin/env python3
"""Shared pytest fixtures for the FastAPI backend."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import app as app_module


@pytest.fixture
def client():
    return TestClient(app_module.app)


@pytest.fixture
def isolated_auth_storage(tmp_path, monkeypatch):
    auth = app_module.auth_service
    users_file = tmp_path / "users.json"
    sessions_file = tmp_path / "sessions.json"
    monkeypatch.setattr(auth, "_users_file", users_file)
    monkeypatch.setattr(auth, "_sessions_file", sessions_file)
    auth._sessions = {}
    auth._refresh_index = {}
    return auth


@pytest.fixture
def isolated_investment_storage(tmp_path, monkeypatch):
    from flask_services.investment_repository import JsonInvestmentRepository
    from api.services import investment_service as inv

    signal_file = tmp_path / "signal_logs.json"
    inv._repo = JsonInvestmentRepository(tmp_path)
    monkeypatch.setattr(inv.signal_tracker, "_file", signal_file)
    inv._portfolio_cache = {}
    inv._outcome_resolver = None
    return inv
