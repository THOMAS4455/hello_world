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

    def record_market_breadth(
        self,
        trading_date: str,
        breadth: float,
        *,
        source: str = "live",
        overwrite: bool = True,
    ) -> bool:
        day = str(trading_date or "").strip()[:10]
        if not day:
            return False
        with self._lock:
            rows = self._load_json_map(self._breadth_file)
            if day in rows and not overwrite:
                return False
            rows[day] = {
                "breadth": float(breadth),
                "source": str(source or "live"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._save_json_map(self._breadth_file, rows)
        return True

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

    def get_status(self) -> Dict[str, Any]:
        breadth_map = self.get_breadth_map()
        breadth_days = sorted(breadth_map.keys())
        return {
            "breadth_days": len(breadth_days),
            "breadth_range": {
                "start": breadth_days[0] if breadth_days else None,
                "end": breadth_days[-1] if breadth_days else None,
            },
            "data_dir": str(self._breadth_file.parent),
        }


feature_history_store = FeatureHistoryStore()
