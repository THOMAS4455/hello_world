"""Tests for the local daily-bar store."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from validation.market_store import MarketStore  # noqa: E402


def _frame(dates, closes, **overrides):
    data = {
        "date": dates,
        "open_price": [c * 0.99 for c in closes],
        "high_price": [c * 1.01 for c in closes],
        "low_price": [c * 0.98 for c in closes],
        "close_price": closes,
        "volume": [1000] * len(closes),
    }
    data.update(overrides)
    return pd.DataFrame(data)


@pytest.fixture()
def store(tmp_path: Path) -> MarketStore:
    return MarketStore(tmp_path / "market.sqlite")


def test_upsert_is_idempotent(store: MarketStore) -> None:
    dates = ["2026-01-02", "2026-01-05", "2026-01-06"]
    frame = _frame(dates, [10.0, 11.0, 12.0])

    first = store.upsert_bars("000001", frame)
    second = store.upsert_bars("000001", frame)

    assert first == 3
    assert second == 3
    assert store.bar_count("000001") == 3, "re-running must not duplicate rows"


def test_upsert_updates_existing_rows(store: MarketStore) -> None:
    store.upsert_bars("000001", _frame(["2026-01-02"], [10.0]))
    store.upsert_bars("000001", _frame(["2026-01-02"], [10.5]))

    bars = store.load_bars("000001")
    assert len(bars) == 1
    assert bars.iloc[0]["close_price"] == pytest.approx(10.5)


def test_missing_required_column_raises(store: MarketStore) -> None:
    bad = pd.DataFrame({"date": ["2026-01-02"], "volume": [1]})
    with pytest.raises(ValueError) as exc:
        store.upsert_bars("000001", bad)
    assert "close_price" in str(exc.value)


def test_empty_frame_is_rejected(store: MarketStore) -> None:
    with pytest.raises(ValueError):
        store.upsert_bars("000001", pd.DataFrame())


def test_load_bars_is_ascending_and_symbol_scoped(store: MarketStore) -> None:
    store.upsert_bars("000001", _frame(["2026-01-06", "2026-01-02"], [12.0, 10.0]))
    store.upsert_bars("600519", _frame(["2026-01-02"], [1700.0]))

    bars = store.load_bars("000001")
    assert list(bars["date"].dt.strftime("%Y-%m-%d")) == ["2026-01-02", "2026-01-06"]
    assert store.bar_count("600519") == 1
    assert store.bar_count("000002") == 0


def test_missing_forward_bars(store: MarketStore) -> None:
    store.upsert_bars("000001", _frame(["2026-01-02", "2026-01-05"], [10.0, 11.0]))

    assert store.missing_forward_bars("000001", "2026-01-02", horizon=5) is True
    assert store.missing_forward_bars("000001", "2026-01-02", horizon=1) is False


def test_coverage_reports_full_population(store: MarketStore) -> None:
    store.upsert_bars("000001", _frame(["2026-01-02"], [10.0]))
    store.upsert_bars("600519", _frame(["2026-01-06"], [1700.0]))

    cov = store.coverage()
    assert cov["symbols"] == 2
    assert cov["rows"] == 2
    assert cov["first_date"] == "2026-01-02"
    assert cov["last_date"] == "2026-01-06"


def test_naive_and_string_dates_are_normalised(store: MarketStore) -> None:
    frame = pd.DataFrame(
        {
            "date": ["2026-01-02", "2026-01-05"],
            "close_price": [10.0, 11.0],
        }
    )
    store.upsert_bars("000001", frame)
    bars = store.load_bars("000001")
    assert len(bars) == 2
    assert bars["close_price"].tolist() == [10.0, 11.0]
