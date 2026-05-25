from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask_services.feature_history_store import FeatureHistoryStore  # noqa: E402


def test_prev_trading_day_uses_stock_calendar():
    dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert FeatureHistoryStore.prev_trading_day(dates, "2024-01-03") == "2024-01-02"
    assert FeatureHistoryStore.prev_trading_day(dates, "2024-01-02") is None


def test_record_and_load_breadth(tmp_path):
    store = FeatureHistoryStore(tmp_path)
    store.record_market_breadth("2024-01-03", 0.12)
    assert store.get_breadth_map()["2024-01-03"] == 0.12


def test_record_breadth_skip_without_overwrite(tmp_path):
    store = FeatureHistoryStore(tmp_path)
    store.record_market_breadth("2024-01-03", 0.12)
    assert store.record_market_breadth("2024-01-03", 0.99, overwrite=False) is False
    assert store.get_breadth_map()["2024-01-03"] == 0.12


def test_get_status_reports_ranges(tmp_path):
    store = FeatureHistoryStore(tmp_path)
    store.record_market_breadth("2024-01-02", 0.1)
    store.record_sentiment_daily(
        "2024-01-04",
        {
            "sentiment_score": 0.2,
            "sentiment_confidence": 0.5,
            "positive_ratio": 0.3,
            "negative_ratio": 0.1,
            "target_match_count": 2,
        },
    )
    status = store.get_status()
    assert status["breadth_days"] == 1
    assert status["sentiment_days"] == 1
    assert status["breadth_range"]["start"] == "2024-01-02"
