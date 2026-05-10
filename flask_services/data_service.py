"""
Data service for stock list/detail based on AKShare.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataService:
    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout = 300
        self.disk_cache_ttl = 24 * 3600
        self.has_real_data = True
        self.stock_source = "akshare_em"
        self.available_stock_sources = {
            "akshare_em": "AKShare Eastmoney",
            "akshare_sina": "AKShare Sina",
        }
        self._refreshing_stocks = False
        self._lock = threading.Lock()
        self.stocks_cache_file = Path(__file__).parent.parent / "data" / "stocks_cache.json"
        self.stocks_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._column_aliases = {
            "symbol": ["代码", "浠ｇ爜"],
            "name": ["名称", "鍚嶇О"],
            "price": ["最新价", "鏈€鏂颁环"],
            "change": ["涨跌额", "娑ㄨ穼棰?"],
            "change_percent": ["涨跌幅", "娑ㄨ穼骞?"],
            "volume": ["成交量", "鎴愪氦閲?"],
            "market_cap": ["总市值", "鎬诲競鍊?"],
            "date": ["日期", "鏃ユ湡"],
            "open": ["开盘", "寮€鐩?"],
            "high": ["最高", "鏈€楂?"],
            "low": ["最低", "鏈€浣?"],
            "close": ["收盘", "鏀剁洏"],
        }

    def _get_cache(self, key: str) -> Optional[Any]:
        payload = self.cache.get(key)
        if not payload:
            return None
        if time.time() - payload["timestamp"] > self.cache_timeout:
            return None
        return payload["data"]

    def _set_cache(self, key: str, data: Any) -> None:
        self.cache[key] = {"timestamp": time.time(), "data": data}

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            import pandas as pd

            if pd.isna(value):
                return default
        except Exception:
            pass
        try:
            return float(value)
        except Exception:
            return default

    def _to_int(self, value: Any, default: int = 0) -> int:
        try:
            import pandas as pd

            if pd.isna(value):
                return default
        except Exception:
            pass
        try:
            return int(float(value))
        except Exception:
            return default

    def _pick_value(self, row: Dict[str, Any], logical_name: str, default: Any = None) -> Any:
        for column in self._column_aliases.get(logical_name, []):
            if column in row:
                return row.get(column, default)
        return row.get(logical_name, default)

    def _parse_stock_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        symbol = str(self._pick_value(row, "symbol", "")).strip()
        name = str(self._pick_value(row, "name", "")).strip()
        if not symbol or not name:
            return None

        price = self._to_float(self._pick_value(row, "price", 0))
        if price <= 0:
            return None

        return {
            "symbol": symbol,
            "name": name,
            "price": price,
            "change": self._to_float(self._pick_value(row, "change", 0)),
            "change_percent": self._to_float(self._pick_value(row, "change_percent", 0)),
            "volume": self._to_int(self._pick_value(row, "volume", 0)),
            "market_cap": self._to_float(self._pick_value(row, "market_cap", 0)),
        }

    def _read_stocks_disk_cache(self) -> Optional[Dict[str, Any]]:
        if not self.stocks_cache_file.exists():
            return None
        try:
            payload = json.loads(self.stocks_cache_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            stocks = payload.get("stocks")
            if not isinstance(stocks, list):
                return None
            return payload
        except Exception:
            return None

    def _write_stocks_disk_cache(self, stocks: List[Dict[str, Any]]) -> None:
        payload = {
            "timestamp": time.time(),
            "last_update": datetime.now().isoformat(),
            "total": len(stocks),
            "stocks": stocks,
        }
        self.stocks_cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _build_stocks_payload(
        self, stocks: List[Dict[str, Any]], total: int, last_update: str
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "stocks": stocks,
                "total": total,
                "returned": len(stocks),
                "last_update": last_update,
            },
        }

    def _refresh_full_stocks_cache_async(self) -> None:
        def runner() -> None:
            try:
                fresh = self._get_real_stocks()
                self._write_stocks_disk_cache(fresh)
                self._set_cache(
                    "stocks_list_full",
                    self._build_stocks_payload(fresh, len(fresh), datetime.now().isoformat()),
                )
            finally:
                with self._lock:
                    self._refreshing_stocks = False

        with self._lock:
            if self._refreshing_stocks:
                return
            self._refreshing_stocks = True

        threading.Thread(target=runner, daemon=True).start()

    def get_data_source_config(self) -> Dict[str, Any]:
        return {
            "stock_source": self.stock_source,
            "available_stock_sources": [
                {"code": code, "name": name}
                for code, name in self.available_stock_sources.items()
            ],
        }

    def set_stock_source(self, source: str) -> Dict[str, Any]:
        source = str(source or "").strip().lower()
        if source not in self.available_stock_sources:
            raise Exception(f"Unsupported stock source: {source}")
        self.stock_source = source
        self.clear_cache()
        return self.get_data_source_config()

    def get_stocks(self, limit: int = 0, force_refresh: bool = False) -> Dict[str, Any]:
        limit = int(limit or 0)
        cache_key = "stocks_list_full"
        if force_refresh:
            try:
                if not self.has_real_data:
                    raise Exception("Real data mode is disabled")
                stocks = self._get_real_stocks()
                self._write_stocks_disk_cache(stocks)
                payload = self._build_stocks_payload(stocks, len(stocks), datetime.now().isoformat())
                self._set_cache(cache_key, payload)
                self.cache.pop("market_overview", None)
                if limit > 0:
                    return self._build_stocks_payload(
                        stocks[:limit], len(stocks), payload["data"]["last_update"]
                    )
                return payload
            except Exception:
                pass

        cached = self._get_cache(cache_key)
        if cached is not None:
            stocks = cached["data"]["stocks"]
            total = cached["data"]["total"]
            last_update = cached["data"].get("last_update", datetime.now().isoformat())
            if limit > 0:
                stocks = stocks[:limit]
            return self._build_stocks_payload(stocks, total, last_update)

        disk_cached = self._read_stocks_disk_cache()
        if disk_cached is not None:
            stocks = disk_cached.get("stocks", [])
            total = int(disk_cached.get("total", len(stocks)))
            last_update = str(disk_cached.get("last_update", datetime.now().isoformat()))
            self._set_cache(cache_key, self._build_stocks_payload(stocks, total, last_update))

            disk_age = time.time() - float(disk_cached.get("timestamp", 0))
            if disk_age > self.disk_cache_ttl and self.has_real_data:
                self._refresh_full_stocks_cache_async()

            if limit > 0:
                stocks = stocks[:limit]
            return self._build_stocks_payload(stocks, total, last_update)

        if not self.has_real_data:
            raise Exception("Real data mode is disabled")

        stocks = self._get_real_stocks()
        self._write_stocks_disk_cache(stocks)
        payload = self._build_stocks_payload(stocks, len(stocks), datetime.now().isoformat())
        self._set_cache(cache_key, payload)
        if limit > 0:
            return self._build_stocks_payload(
                stocks[:limit], len(stocks), payload["data"]["last_update"]
            )
        return payload

    def _get_real_stocks(self) -> List[Dict[str, Any]]:
        import akshare as ak

        stock_df = self._fetch_spot_df(ak)
        records = stock_df.to_dict("records")
        stocks: List[Dict[str, Any]] = []
        for row in records:
            parsed = self._parse_stock_row(row)
            if parsed is not None:
                stocks.append(parsed)
        return stocks

    def _fetch_spot_df(self, ak_module: Any):
        if self.stock_source == "akshare_em":
            return ak_module.stock_zh_a_spot_em()
        if self.stock_source == "akshare_sina":
            return ak_module.stock_zh_a_spot()
        raise Exception(f"Unsupported stock source: {self.stock_source}")

    def get_stock_detail(self, symbol: str) -> Dict[str, Any]:
        cache_key = f"stock_detail_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        detail = self._get_real_stock_detail(symbol)
        self._set_cache(cache_key, detail)
        return detail

    def _find_from_cached_stock_list(self, symbol: str) -> Optional[Dict[str, Any]]:
        cached_list = self._get_cache("stocks_list_full")
        if not cached_list:
            return None
        stocks = cached_list.get("data", {}).get("stocks", [])
        for item in stocks:
            if str(item.get("symbol")) == symbol:
                return item
        return None

    def _get_real_stock_detail(self, symbol: str) -> Dict[str, Any]:
        import akshare as ak

        base = self._find_from_cached_stock_list(symbol)
        if base is None:
            stock_df = self._fetch_spot_df(ak)
            symbol_column = next(
                (column for column in self._column_aliases["symbol"] if column in stock_df.columns),
                self._column_aliases["symbol"][0],
            )
            stock_row = stock_df[stock_df[symbol_column] == symbol]
            if stock_row.empty:
                raise Exception(f"Stock {symbol} not found")
            base = self._parse_stock_row(stock_row.iloc[0].to_dict())
            if base is None:
                raise Exception(f"Stock {symbol} data parse failed")

        history: List[Dict[str, Any]] = []
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
            history_df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="",
            )
            if not history_df.empty:
                for _, row in history_df.tail(60).iterrows():
                    date_value = self._pick_value(row, "date")
                    if hasattr(date_value, "strftime"):
                        date_text = date_value.strftime("%Y-%m-%d")
                    else:
                        date_text = str(date_value)
                    history.append(
                        {
                            "date": date_text,
                            "open": self._to_float(self._pick_value(row, "open", 0)),
                            "high": self._to_float(self._pick_value(row, "high", 0)),
                            "low": self._to_float(self._pick_value(row, "low", 0)),
                            "close": self._to_float(self._pick_value(row, "close", 0)),
                            "volume": self._to_int(self._pick_value(row, "volume", 0)),
                        }
                    )
        except Exception:
            history = []

        return {
            "symbol": symbol,
            "name": base["name"],
            "price": base["price"],
            "current_price": base["price"],
            "change": base["change"],
            "change_percent": base["change_percent"],
            "volume": base["volume"],
            "market_cap": base["market_cap"],
            "history": history,
            "timestamp": datetime.now().isoformat(),
        }

    def get_market_overview(self, force_refresh: bool = False) -> Dict[str, Any]:
        cache_key = "market_overview"
        if force_refresh:
            try:
                stocks_data = self.get_stocks(limit=0, force_refresh=True)
                stocks = stocks_data["data"]["stocks"]
                if not stocks:
                    raise Exception("No stock data")
            except Exception:
                cached = self._get_cache(cache_key)
                if cached is not None:
                    return cached
                stocks_data = self.get_stocks(limit=0, force_refresh=False)
                stocks = stocks_data["data"]["stocks"]
        else:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return cached
            stocks_data = self.get_stocks(limit=0, force_refresh=False)
            stocks = stocks_data["data"]["stocks"]

        if not stocks:
            raise Exception("No stock data")

        total_stocks = len(stocks)
        rising_stocks = len([stock for stock in stocks if stock["change"] > 0])
        falling_stocks = len([stock for stock in stocks if stock["change"] < 0])
        flat_stocks = total_stocks - rising_stocks - falling_stocks
        avg_change = sum(stock["change_percent"] for stock in stocks) / total_stocks

        top_gainer = max(stocks, key=lambda item: item["change_percent"])
        top_loser = min(stocks, key=lambda item: item["change_percent"])

        overview = {
            "total_stocks": total_stocks,
            "rising_stocks": rising_stocks,
            "falling_stocks": falling_stocks,
            "flat_stocks": flat_stocks,
            "avg_change_percent": avg_change,
            "top_gainer": {
                "symbol": top_gainer["symbol"],
                "name": top_gainer["name"],
                "change_percent": top_gainer["change_percent"],
            },
            "top_loser": {
                "symbol": top_loser["symbol"],
                "name": top_loser["name"],
                "change_percent": top_loser["change_percent"],
            },
            "timestamp": datetime.now().isoformat(),
        }
        self._set_cache(cache_key, overview)
        return overview

    def clear_cache(self) -> None:
        self.cache.clear()


data_service = DataService()
