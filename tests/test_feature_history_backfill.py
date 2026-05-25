from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask_services.feature_history_backfill import FeatureHistoryBackfillService  # noqa: E402
from flask_services.feature_history_store import FeatureHistoryStore  # noqa: E402


def test_get_status_empty_store(tmp_path):
    store = FeatureHistoryStore(tmp_path)
    service = FeatureHistoryBackfillService(store)
    status = service.get_status()
    assert status["breadth_days"] == 0
    assert status["sentiment_days"] == 0


def test_backfill_sentiment_respects_overwrite(tmp_path, monkeypatch):
    day = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    store = FeatureHistoryStore(tmp_path)
    store.record_sentiment_daily(
        day,
        {"sentiment_score": 0.1, "sentiment_confidence": 0.5, "positive_ratio": 0.2, "negative_ratio": 0.1, "target_match_count": 3},
    )
    service = FeatureHistoryBackfillService(store)

    fake_prediction = MagicMock()
    fake_prediction._fetch_recent_news_items.return_value = [
        {"title": "利好上涨", "time": day},
    ]
    fake_prediction._build_daily_sentiment_map.return_value = {
        day: {
            "sentiment_score": 0.9,
            "sentiment_confidence": 0.8,
            "positive_ratio": 0.7,
            "negative_ratio": 0.1,
            "target_match_count": 5,
        }
    }
    monkeypatch.setattr("flask_services.prediction_service.prediction_service", fake_prediction)

    result = service.run(days=30, news_limit=50, fill_sentiment=True, fill_breadth=False, overwrite=False)
    assert result["sentiment"]["skipped"] == 1
    assert store.get_sentiment_map()[day]["sentiment_score"] == 0.1

    service.run(days=30, news_limit=50, fill_sentiment=True, fill_breadth=False, overwrite=True)
    assert store.get_sentiment_map()[day]["sentiment_score"] == 0.9


def test_backfill_breadth_index_proxy(tmp_path, monkeypatch):
    store = FeatureHistoryStore(tmp_path)
    service = FeatureHistoryBackfillService(store)

    d1 = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    d2 = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    d3 = datetime.now().strftime("%Y-%m-%d")
    frame = pd.DataFrame({"日期": [d1, d2, d3], "收盘": [3000.0, 3030.0, 2990.0]})

    fake_ak = MagicMock()
    fake_ak.stock_zh_index_daily_em.return_value = frame
    monkeypatch.setitem(sys.modules, "akshare", fake_ak)

    result = service.run(days=10, fill_sentiment=False, fill_breadth=True, overwrite=True)
    breadth = store.get_breadth_map()
    assert result["breadth"]["written"] >= 2
    assert d2 in breadth
    assert -1.0 <= breadth[d2] <= 1.0
