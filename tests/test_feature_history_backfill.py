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

    result = service.run(days=10, fill_breadth=True, overwrite=True)
    breadth = store.get_breadth_map()
    assert result["breadth"]["written"] >= 2
    assert d2 in breadth
    assert -1.0 <= breadth[d2] <= 1.0
