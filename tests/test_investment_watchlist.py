"""Tests for investment service watchlist and config."""

from pathlib import Path

import pytest

from flask_services.investment_service import InvestmentService


@pytest.fixture
def investment_svc(tmp_path, monkeypatch):
    from flask_services.investment_repository import JsonInvestmentRepository

    svc = InvestmentService()
    svc._repo = JsonInvestmentRepository(tmp_path)
    monkeypatch.setattr(svc.signal_tracker, "_file", tmp_path / "signal_logs.json")
    return svc


def test_watchlist_crud(investment_svc):
    user_id = 42
    updated = investment_svc.update_watchlist(user_id, ["000001", "600000", "000001"])
    assert updated["symbols"] == ["000001", "600000"]

    watch = investment_svc.get_watchlist(user_id)
    assert watch["symbols"] == ["000001", "600000"]
    assert watch["config"]["horizon"] == 5


def test_risk_level_mapping(investment_svc):
    user_id = 3
    investment_svc.update_portfolio_config(user_id, {"risk_level": "conservative"})
    cfg = investment_svc.get_portfolio_config(user_id)
    assert cfg["min_confidence"] >= 0.65
    assert cfg["max_total_equity_pct"] <= 0.60


def test_portfolio_config_update(investment_svc):
    user_id = 7
    investment_svc.update_watchlist(user_id, ["920978"])
    cfg = investment_svc.update_portfolio_config(user_id, {"risk_level": "aggressive", "horizon": 7})
    assert cfg["risk_level"] == "aggressive"
    assert cfg["horizon"] == 7
