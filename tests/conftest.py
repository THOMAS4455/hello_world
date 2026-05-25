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
