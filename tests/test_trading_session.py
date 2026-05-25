from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from flask_services.data_service import DataService


def _shanghai(day: str, hour: int, minute: int = 0) -> datetime:
    return datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}:00").replace(tzinfo=ZoneInfo("Asia/Shanghai"))


def test_effective_trading_date_during_session():
    service = DataService()
    now = _shanghai("2026-05-25", 10, 30)
    assert service._effective_trading_date(now) == "2026-05-25"


def test_effective_trading_date_before_open():
    service = DataService()
    now = _shanghai("2026-05-26", 8, 30)
    assert service._effective_trading_date(now) == "2026-05-25"


def test_effective_trading_date_on_weekend():
    service = DataService()
    now = _shanghai("2026-05-24", 11, 0)
    assert service._effective_trading_date(now) == "2026-05-22"


def test_should_fetch_live_outside_session_without_force():
    service = DataService()
    now = _shanghai("2026-05-25", 20, 0)
    with patch.object(service, "_beijing_now", return_value=now):
        assert service._should_fetch_live(False) is False
        assert service._should_fetch_live(True) is True


def test_get_stocks_uses_snapshot_outside_session(monkeypatch):
    service = DataService()
    now = _shanghai("2026-05-25", 20, 0)
    snapshot = {
        "timestamp": 1,
        "last_update": "2026-05-25T15:00:00",
        "trading_date": "2026-05-25",
        "source": "aggregate_realtime",
        "stocks": [{"symbol": "000001", "name": "PingAn", "price": 10.0, "change": 0.1, "change_percent": 1.0, "volume": 1, "market_cap": 1}],
        "total": 1,
    }

    monkeypatch.setattr(service, "_beijing_now", lambda: now)
    monkeypatch.setattr(service, "_get_trading_day_snapshot", lambda trading_date: snapshot)
    monkeypatch.setattr(service, "_fetch_live_payload", lambda: (_ for _ in ()).throw(AssertionError("should not fetch live")))

    payload = service.get_stocks(limit=0, force_refresh=False)
    data = payload["data"]
    assert data["stocks"][0]["symbol"] == "000001"
    assert data["freshness"]["refresh_skipped"] is True
    assert data["freshness"]["in_trading_session"] is False
