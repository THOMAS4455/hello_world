"""Tests for outcome resolver."""

from pathlib import Path
import sys

import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from validation.outcome_resolver import OutcomeResolver
from validation.signal_tracker import SignalTracker


def _price_loader(symbol: str) -> pd.DataFrame:
    prices = [10.0 + i * 0.5 for i in range(30)]
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=30, freq="B"),
            "close_price": prices,
        }
    )


@pytest.fixture
def resolver(tmp_path):
    tracker = SignalTracker(tmp_path / "signals.json")
    return OutcomeResolver(tracker, _price_loader)


def test_resolve_pending_fixed_horizon(resolver):
    resolver.signal_tracker.record(
        symbol="000001",
        prediction=1,
        direction="up",
        confidence=0.7,
        horizon=5,
        up_threshold=0.02,
    )
    with resolver.signal_tracker._lock:
        payload = resolver.signal_tracker._load()
        payload["logs"][0]["recorded_at"] = pd.Timestamp("2025-01-06").timestamp()
        resolver.signal_tracker._save(payload)
    updated = resolver.resolve_pending(label_mode="fixed_horizon")
    assert updated == 1
    stats = resolver.signal_tracker.get_stats("000001")
    assert stats["samples"] == 1
    assert stats["avg_return"] != 0.0
