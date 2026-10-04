"""
Batch backfill for point-in-time market breadth features.

Breadth backfill uses CSI/Shanghai index daily returns as a bounded proxy when
historical advance/decline counts are unavailable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask_services.feature_history_store import FeatureHistoryStore, feature_history_store


class FeatureHistoryBackfillService:
    MAX_DAYS = 365
    INDEX_PROXY_SCALE = 0.03

    def __init__(self, store: Optional[FeatureHistoryStore] = None) -> None:
        self.store = store or feature_history_store

    def get_status(self) -> Dict[str, Any]:
        return dict(self.store.get_status())

    def run(
        self,
        *,
        days: int = 90,
        fill_breadth: bool = True,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        window_days = max(1, min(int(days or 90), self.MAX_DAYS))
        cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

        result: Dict[str, Any] = {
            "requested_days": window_days,
            "cutoff_date": cutoff,
            "overwrite": bool(overwrite),
            "breadth": {"enabled": fill_breadth, "written": 0, "skipped": 0, "days": 0, "source": "index_proxy"},
            "errors": [],
        }

        if fill_breadth:
            try:
                breadth_stats = self._backfill_breadth_index_proxy(window_days, cutoff, overwrite)
                result["breadth"].update(breadth_stats)
            except Exception as exc:
                result["errors"].append(f"breadth: {exc}")

        result["status"] = self.get_status()
        return result

    def _backfill_breadth_index_proxy(
        self, window_days: int, cutoff: str, overwrite: bool
    ) -> Dict[str, Any]:
        proxy_map = self._fetch_index_breadth_proxy(window_days)
        written = 0
        skipped = 0
        for day, breadth in proxy_map.items():
            if str(day)[:10] < cutoff:
                continue
            if self.store.record_market_breadth(
                day, breadth, source="index_proxy", overwrite=overwrite
            ):
                written += 1
            else:
                skipped += 1
        return {"written": written, "skipped": skipped, "days": len(proxy_map)}

    def _fetch_index_breadth_proxy(self, window_days: int) -> Dict[str, float]:
        import akshare as ak
        import pandas as pd

        df = ak.stock_zh_index_daily_em(symbol="sh000001")
        if df is None or df.empty:
            raise Exception("index daily series is empty")

        date_col = self._resolve_column(df, ("date", "日期"))
        close_col = self._resolve_column(df, ("close", "收盘", "收盘价"))
        if not date_col or not close_col:
            raise Exception("index daily columns not recognized")

        frame = df[[date_col, close_col]].copy()
        frame.columns = ["date", "close"]
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["date", "close"]).sort_values("date")
        frame["pct"] = frame["close"].pct_change()
        frame = frame.tail(max(5, int(window_days) + 5))

        out: Dict[str, float] = {}
        for _, row in frame.iterrows():
            day = row["date"].strftime("%Y-%m-%d")
            pct = float(row["pct"]) if row["pct"] == row["pct"] else 0.0
            proxy = max(-1.0, min(1.0, pct / self.INDEX_PROXY_SCALE))
            out[day] = round(proxy, 6)
        return out

    @staticmethod
    def _resolve_column(df: Any, candidates: tuple[str, ...]) -> Optional[str]:
        columns = {str(col).strip().lower(): col for col in df.columns}
        for name in candidates:
            key = name.lower()
            if key in columns:
                return columns[key]
        return None


feature_history_backfill_service = FeatureHistoryBackfillService()
