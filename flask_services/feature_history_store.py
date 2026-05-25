"""
Persist daily market breadth and sentiment for point-in-time feature replay.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class FeatureHistoryStore:
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        root = data_dir or Path(__file__).parent.parent / "data" / "feature_history"
        root.mkdir(parents=True, exist_ok=True)
        self._breadth_file = root / "market_breadth_daily.json"
        self._sentiment_file = root / "sentiment_daily.json"
        self._lock = threading.RLock()

    def _load_json_map(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_json_map(self, path: Path, payload: Dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_market_breadth(self, trading_date: str, breadth: float) -> None:
        day = str(trading_date or "").strip()[:10]
        if not day:
            return
        with self._lock:
            rows = self._load_json_map(self._breadth_file)
            rows[day] = {
                "breadth": float(breadth),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._save_json_map(self._breadth_file, rows)

    def record_sentiment_daily(self, trading_date: str, metrics: Dict[str, float]) -> None:
        day = str(trading_date or "").strip()[:10]
        if not day:
            return
        with self._lock:
            rows = self._load_json_map(self._sentiment_file)
            rows[day] = {
                **{k: float(v) for k, v in metrics.items()},
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._save_json_map(self._sentiment_file, rows)

    def get_breadth_map(self) -> Dict[str, float]:
        with self._lock:
            raw = self._load_json_map(self._breadth_file)
        out: Dict[str, float] = {}
        for day, value in raw.items():
            if isinstance(value, dict):
                out[str(day)[:10]] = float(value.get("breadth", 0.0) or 0.0)
            else:
                out[str(day)[:10]] = float(value or 0.0)
        return out

    def get_sentiment_map(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            raw = self._load_json_map(self._sentiment_file)
        out: Dict[str, Dict[str, float]] = {}
        for day, value in raw.items():
            if not isinstance(value, dict):
                continue
            out[str(day)[:10]] = {
                "sentiment_score": float(value.get("sentiment_score", 0.0) or 0.0),
                "sentiment_confidence": float(value.get("sentiment_confidence", 0.0) or 0.0),
                "positive_ratio": float(value.get("positive_ratio", 0.0) or 0.0),
                "negative_ratio": float(value.get("negative_ratio", 0.0) or 0.0),
                "target_match_count": float(value.get("target_match_count", 0.0) or 0.0),
            }
        return out

    @staticmethod
    def prev_trading_day(trading_dates: List[str], current: str) -> Optional[str]:
        day = str(current or "").strip()[:10]
        if not day or not trading_dates:
            return None
        dates = sorted({str(d)[:10] for d in trading_dates if d})
        try:
            idx = dates.index(day)
        except ValueError:
            prior = [d for d in dates if d < day]
            return prior[-1] if prior else None
        return dates[idx - 1] if idx > 0 else None


feature_history_store = FeatureHistoryStore()
