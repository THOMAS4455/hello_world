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
