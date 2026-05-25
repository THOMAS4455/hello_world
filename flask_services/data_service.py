"""
Realtime stock data service backed by multiple live A-share sources.

Strategy:
1. Use AKShare Sina for the full market universe and baseline quotes.
2. Verify and enrich quotes in bulk with direct Sina and Tencent endpoints.
3. Expose source freshness and health so stale fallbacks are never silent.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

import requests


class DataService:
    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout = 60
        self.disk_cache_ttl = 24 * 3600
        self.max_stale_fallback = 3 * 24 * 3600
        self.live_only_market_data = True
        self.trading_session_aware = True
        self.intraday_cache_timeout = 60
        self.market_timezone = ZoneInfo("Asia/Shanghai")
        self._last_live_stocks: List[Dict[str, Any]] = []
        self.has_real_data = True
        self.stock_source = "aggregate_realtime"
        self.source_retry_count = 3
        self.source_retry_delay = 0.8
        self.quote_batch_size = 180
        self.request_timeout = 20
        self.eastmoney_request_timeout = 25
        self.min_baseline_universe = 500
        self.eastmoney_page_size = 100
        self.eastmoney_max_pages = 80
        self.eastmoney_direct_hosts = (
            "https://push2delay.eastmoney.com/api/qt/clist/get",
            "https://push2.eastmoney.com/api/qt/clist/get",
            "https://82.push2.eastmoney.com/api/qt/clist/get",
            "https://80.push2.eastmoney.com/api/qt/clist/get",
            "https://81.push2.eastmoney.com/api/qt/clist/get",
        )
        self.available_stock_sources = {
            "aggregate_realtime": "Aggregate Realtime (AKShare + Sina + Tencent)",
            "akshare_sina": "AKShare Sina",
            "direct_sina": "Direct Sina",
            "direct_tencent": "Direct Tencent",
            "akshare_em": "AKShare Eastmoney",
            "eastmoney_direct": "Eastmoney Direct",
        }
        self._refreshing_stocks = False
        self._lock = Lock()
        self.stocks_cache_file = Path(__file__).parent.parent / "data" / "stocks_cache.json"
        self.stocks_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.last_refresh_status: Dict[str, Any] = {
            "last_attempt_at": None,
            "last_success_at": None,
            "last_success_source": None,
            "last_error": None,
            "last_error_source": None,
        }
        self.source_health: Dict[str, Dict[str, Any]] = {}
        self._column_aliases = {
            "symbol": ["代码", "symbol"],
            "name": ["名称", "name"],
            "price": ["最新价", "现价", "price"],
            "change": ["涨跌额", "change"],
            "change_percent": ["涨跌幅", "changepercent", "change_percent"],
            "volume": ["成交量", "volume"],
            "market_cap": ["总市值", "market_cap"],
            "date": ["日期", "date"],
            "open": ["开盘", "open"],
            "high": ["最高", "high"],
            "low": ["最低", "low"],
            "close": ["收盘", "close"],
        }

    def _now_iso(self) -> str:
        return datetime.now().isoformat()

    def _beijing_now(self) -> datetime:
        return datetime.now(self.market_timezone)

    def _previous_weekday(self, day: datetime) -> datetime:
        cursor = day - timedelta(days=1)
        while cursor.weekday() >= 5:
            cursor -= timedelta(days=1)
        return cursor

    def _effective_trading_date(self, now: Optional[datetime] = None) -> str:
        current = now or self._beijing_now()
        if current.weekday() >= 5:
            return self._previous_weekday(current).date().isoformat()

        session_open = current.replace(hour=9, minute=25, second=0, microsecond=0)
        if current < session_open:
            return self._previous_weekday(current).date().isoformat()
        return current.date().isoformat()

    def _is_in_trading_session(self, now: Optional[datetime] = None) -> bool:
        current = now or self._beijing_now()
        if current.weekday() >= 5:
            return False
        session_open = current.replace(hour=9, minute=25, second=0, microsecond=0)
        session_close = current.replace(hour=15, minute=0, second=0, microsecond=0)
        return session_open <= current <= session_close

    def get_trading_session_status(self) -> Dict[str, Any]:
        now = self._beijing_now()
        return {
            "timezone": "Asia/Shanghai",
            "now": now.isoformat(),
            "effective_trading_date": self._effective_trading_date(now),
            "in_trading_session": self._is_in_trading_session(now),
            "session_window": "09:25-15:00",
            "should_auto_refresh": self._is_in_trading_session(now),
        }

    def _should_fetch_live(self, force_refresh: bool) -> bool:
        if not self.trading_session_aware:
            return True
        if force_refresh:
            return True
        return self._is_in_trading_session()

    def _get_session_memory_cache(self, cache_key: str, trading_date: str) -> Optional[Any]:
        entry = self.cache.get(cache_key)
        if not entry:
            return None
        meta = entry.get("meta") or {}
        if meta.get("trading_date") != trading_date:
            return None
        if self._is_in_trading_session():
            if time.time() - float(entry.get("timestamp", 0)) > self.intraday_cache_timeout:
                return None
        return entry.get("data")

    def _set_session_memory_cache(self, cache_key: str, trading_date: str, payload: Any) -> None:
        self.cache[cache_key] = {
            "timestamp": time.time(),
            "data": payload,
            "meta": {"trading_date": trading_date},
        }

    def _disk_matches_trading_date(self, disk_cached: Dict[str, Any], trading_date: str) -> bool:
        if str(disk_cached.get("trading_date") or "") == trading_date:
            return True
        last_update = str(disk_cached.get("last_update") or "")
        return last_update.startswith(trading_date)

    def _get_trading_day_snapshot(self, trading_date: str) -> Optional[Dict[str, Any]]:
        disk_cached = self._read_stocks_disk_cache()
        if not disk_cached:
            return None
        if not isinstance(disk_cached.get("stocks"), list) or not disk_cached["stocks"]:
            return None
        if not self._disk_matches_trading_date(disk_cached, trading_date):
            return None
        return disk_cached

    def _enrich_freshness(self, freshness: Dict[str, Any], *, refresh_skipped: bool = False) -> Dict[str, Any]:
        enriched = dict(freshness)
        enriched.update(self.get_trading_session_status())
        enriched["refresh_skipped"] = refresh_skipped
        return enriched

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
        return default

    def _normalize_symbol(self, value: Any) -> str:
        symbol = str(value or "").strip().lower()
        if symbol.startswith(("sh", "sz", "bj")):
            symbol = symbol[2:]
        return symbol

    def _symbols_match(self, left: Any, right: Any) -> bool:
        return self._normalize_symbol(left) == self._normalize_symbol(right)

    def _to_market_symbol(self, symbol: str) -> str:
        code = self._normalize_symbol(symbol)
        if code.startswith("6"):
            return f"sh{code}"
        if code.startswith(("0", "3")):
            return f"sz{code}"
        if code.startswith(("4", "8", "9")):
            return f"bj{code}"
        return f"sz{code}"

    def _parse_stock_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        symbol = self._normalize_symbol(self._pick_value(row, "symbol", ""))
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

    def _write_stocks_disk_cache(
        self,
        stocks: List[Dict[str, Any]],
        *,
        source: str,
        fetched_at: str,
        quote_timestamp: Optional[str] = None,
        source_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "timestamp": time.time(),
            "last_update": fetched_at,
            "trading_date": self._effective_trading_date(),
            "source": source,
            "quote_timestamp": quote_timestamp or "",
            "source_summary": source_summary or {},
            "total": len(stocks),
            "stocks": stocks,
        }
        self.stocks_cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _build_freshness(
        self,
        *,
        source: str,
        fetched_at: str,
        cache_origin: str,
        is_live: bool,
        last_error: Optional[str] = None,
        quote_timestamp: str = "",
        source_summary: Optional[Dict[str, Any]] = None,
        refresh_skipped: bool = False,
    ) -> Dict[str, Any]:
        stale_seconds = max(0.0, (datetime.now() - datetime.fromisoformat(fetched_at)).total_seconds())
        freshness = {
            "source": source,
            "fetched_at": fetched_at,
            "quote_timestamp": quote_timestamp,
            "cache_origin": cache_origin,
            "is_live": is_live,
            "is_stale": not is_live,
            "stale_seconds": round(stale_seconds, 3),
            "last_error": last_error or "",
            "source_summary": source_summary or {},
            "source_health": dict(self.source_health),
        }
        if self.trading_session_aware:
            return self._enrich_freshness(freshness, refresh_skipped=refresh_skipped)
        return freshness

    def _build_stocks_payload(
        self,
        stocks: List[Dict[str, Any]],
        total: int,
        last_update: str,
        *,
        source: str,
        cache_origin: str,
        is_live: bool,
        last_error: Optional[str] = None,
        quote_timestamp: str = "",
        source_summary: Optional[Dict[str, Any]] = None,
        refresh_skipped: bool = False,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "stocks": stocks,
                "total": total,
                "returned": len(stocks),
                "last_update": last_update,
                "freshness": self._build_freshness(
                    source=source,
                    fetched_at=last_update,
                    cache_origin=cache_origin,
                    is_live=is_live,
                    last_error=last_error,
                    quote_timestamp=quote_timestamp,
                    source_summary=source_summary,
                    refresh_skipped=refresh_skipped,
                ),
            },
        }

    def _record_source_health(
        self,
        source: str,
        *,
        success: bool,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        item_count: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        current = self.source_health.get(source, {})
        payload = {
            "source": source,
            "success": success,
            "latency_ms": round(latency_ms, 2) if latency_ms is not None else current.get("latency_ms"),
            "last_checked_at": self._now_iso(),
            "last_error": error or "",
            "item_count": item_count if item_count is not None else current.get("item_count"),
            "last_success_at": current.get("last_success_at"),
        }
        if success:
            payload["last_success_at"] = payload["last_checked_at"]
        if isinstance(extra, dict):
            payload.update(extra)
        self.source_health[source] = payload

    def _candidate_sources(self) -> List[str]:
        if self.stock_source == "aggregate_realtime":
            return ["aggregate_realtime"]
        return [self.stock_source]

    def _record_refresh_attempt(
        self,
        *,
        success: bool,
        source: Optional[str],
        error: Optional[str] = None,
    ) -> None:
        now = self._now_iso()
        self.last_refresh_status["last_attempt_at"] = now
        if success:
            self.last_refresh_status["last_success_at"] = now
            self.last_refresh_status["last_success_source"] = source
            self.last_refresh_status["last_error"] = None
            self.last_refresh_status["last_error_source"] = None
        else:
            self.last_refresh_status["last_error"] = error
            self.last_refresh_status["last_error_source"] = source

    def _refresh_full_stocks_cache_async(self) -> None:
        def runner() -> None:
            try:
                payload = self._fetch_live_payload()
                self._write_stocks_disk_cache(
                    payload["stocks"],
                    source=payload["source"],
                    fetched_at=payload["fetched_at"],
                    quote_timestamp=payload["quote_timestamp"],
                    source_summary=payload.get("source_summary"),
                )
                self._set_cache(
                    "stocks_list_full",
                    self._build_stocks_payload(
                        payload["stocks"],
                        len(payload["stocks"]),
                        payload["fetched_at"],
                        source=payload["source"],
                        cache_origin="memory",
                        is_live=True,
                        quote_timestamp=payload["quote_timestamp"],
                        source_summary=payload.get("source_summary"),
                    ),
                )
            finally:
                with self._lock:
                    self._refreshing_stocks = False

        with self._lock:
            if self._refreshing_stocks:
                return
            self._refreshing_stocks = True

        Thread(target=runner, daemon=True).start()

    def get_data_source_config(self) -> Dict[str, Any]:
        return {
            "stock_source": self.stock_source,
            "available_stock_sources": [
                {"code": code, "name": name}
                for code, name in self.available_stock_sources.items()
            ],
            "refresh_status": dict(self.last_refresh_status),
            "source_health": dict(self.source_health),
        }

    def get_data_health(self) -> Dict[str, Any]:
        source_health = dict(self.source_health)
        healthy_sources = sum(1 for item in source_health.values() if item.get("success"))
        last_live_count = len(self._last_live_stocks)
        return {
            "live_only": self.live_only_market_data,
            "trading_session_aware": self.trading_session_aware,
            "stock_source": self.stock_source,
            "refresh_status": dict(self.last_refresh_status),
            "source_health": source_health,
            "healthy_sources": healthy_sources,
            "total_sources": len(source_health),
            "last_live_universe_size": last_live_count,
            "min_baseline_universe": self.min_baseline_universe,
            "is_partial_universe": 0 < last_live_count < self.min_baseline_universe,
            "trading_session": self.get_trading_session_status(),
            "timestamp": time.time(),
        }

    def set_stock_source(self, source: str) -> Dict[str, Any]:
        source = str(source or "").strip().lower()
        if source not in self.available_stock_sources:
            raise Exception(f"Unsupported stock source: {source}")
        self.stock_source = source
        self.clear_cache()
        return self.get_data_source_config()

    def _fetch_spot_df_from_source(self, ak_module: Any, source: str):
        if source == "akshare_em":
            return ak_module.stock_zh_a_spot_em()
        if source == "akshare_sina":
            return ak_module.stock_zh_a_spot()
        raise Exception(f"Unsupported AKShare stock source: {source}")

    def _fetch_spot_df_with_retry(self, ak_module: Any, source: str):
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.source_retry_count + 1):
            try:
                started = time.time()
                with self._disable_proxy_env():
                    stock_df = self._fetch_spot_df_from_source(ak_module, source)
                self._record_source_health(
                    source,
                    success=True,
                    latency_ms=(time.time() - started) * 1000,
                    item_count=int(getattr(stock_df, "shape", [0])[0]),
                )
                return stock_df
            except Exception as exc:
                last_exc = exc
                self._record_source_health(source, success=False, error=str(exc))
                if attempt < self.source_retry_count:
                    time.sleep(self.source_retry_delay)
        raise last_exc if last_exc is not None else Exception(f"{source} fetch failed")

    def _extract_quote_timestamp(self, stock_df: Any) -> str:
        try:
            if "时间戳" in stock_df.columns and not stock_df.empty:
                return str(stock_df.iloc[0].get("时间戳", "") or "").strip()
        except Exception:
            pass
        return ""

    def _chunked(self, items: List[str], size: int) -> Iterable[List[str]]:
        for idx in range(0, len(items), size):
            yield items[idx : idx + size]

    def _create_http_session(self) -> requests.Session:
        session = requests.Session()
        session.trust_env = False
        return session

    def _get_http_text(self, url: str, *, headers: Optional[Dict[str, str]] = None) -> str:
        last_exc: Optional[Exception] = None
        session = self._create_http_session()
        for attempt in range(1, self.source_retry_count + 1):
            try:
                response = session.get(url, headers=headers or {}, timeout=self.request_timeout)
                response.raise_for_status()
                return response.text
            except Exception as exc:
                last_exc = exc
                if attempt < self.source_retry_count:
                    time.sleep(self.source_retry_delay)
        raise last_exc if last_exc is not None else Exception(f"request failed: {url}")

    @contextmanager
    def _disable_proxy_env(self):
        proxy_keys = (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "http_proxy",
            "https_proxy",
            "ALL_PROXY",
            "all_proxy",
        )
        saved = {key: os.environ[key] for key in proxy_keys if key in os.environ}
        saved_no_proxy = {
            key: os.environ[key]
            for key in ("NO_PROXY", "no_proxy")
            if key in os.environ
        }
        for key in proxy_keys:
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"
        try:
            yield
        finally:
            for key in proxy_keys:
                os.environ.pop(key, None)
            for key in ("NO_PROXY", "no_proxy"):
                os.environ.pop(key, None)
            os.environ.update(saved)
            os.environ.update(saved_no_proxy)

    def _get_http_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        last_exc: Optional[Exception] = None
        session = self._create_http_session()
        request_timeout = self.request_timeout if timeout is None else timeout
        for attempt in range(1, self.source_retry_count + 1):
            try:
                response = session.get(
                    url,
                    params=params or {},
                    headers=headers or {},
                    timeout=request_timeout,
                )
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_exc = exc
                if attempt < self.source_retry_count:
                    time.sleep(self.source_retry_delay)
        raise last_exc if last_exc is not None else Exception(f"request failed: {url}")

    def _parse_sina_direct_batch(self, text: str) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or '="' not in line:
                continue
            prefix, payload = line.split('="', 1)
            body = payload.rsplit('"', 1)[0]
            market_symbol = prefix.split("hq_str_", 1)[-1]
            symbol = self._normalize_symbol(market_symbol)
            fields = body.split(",")
            if len(fields) < 32 or not fields[0]:
                continue
            name = fields[0].strip()
            open_price = self._to_float(fields[1], 0)
            prev_close = self._to_float(fields[2], 0)
            price = self._to_float(fields[3], 0)
            high = self._to_float(fields[4], 0)
            low = self._to_float(fields[5], 0)
            volume = self._to_int(fields[8], 0)
            timestamp = f"{fields[30].strip()} {fields[31].strip()}".strip()
            change = price - prev_close if prev_close else 0.0
            change_percent = (change / prev_close * 100) if prev_close else 0.0
            result[symbol] = {
                "symbol": symbol,
                "name": name,
                "price": price,
                "change": round(change, 4),
                "change_percent": round(change_percent, 4),
                "volume": volume,
                "high": high,
                "low": low,
                "open": open_price,
                "quote_timestamp": timestamp,
                "quote_source": "direct_sina",
            }
        return result

    def _parse_tencent_direct_batch(self, text: str) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for raw_line in text.split(";"):
            line = raw_line.strip()
            if not line or '="' not in line:
                continue
            prefix, payload = line.split('="', 1)
            body = payload.rsplit('"', 1)[0]
            if not body:
                continue
            market_symbol = prefix.split("v_", 1)[-1]
            symbol = self._normalize_symbol(market_symbol)
            fields = body.split("~")
            if len(fields) < 35:
                continue
            name = fields[1].strip()
            price = self._to_float(fields[3], 0)
            prev_close = self._to_float(fields[4], 0)
            high = self._to_float(fields[33], 0)
            low = self._to_float(fields[34], 0)
            volume = self._to_int(fields[6], 0) * 100
            timestamp_raw = fields[30].strip()
            timestamp = ""
            if len(timestamp_raw) >= 14:
                timestamp = (
                    f"{timestamp_raw[0:4]}-{timestamp_raw[4:6]}-{timestamp_raw[6:8]} "
                    f"{timestamp_raw[8:10]}:{timestamp_raw[10:12]}:{timestamp_raw[12:14]}"
                )
            change = price - prev_close if prev_close else self._to_float(fields[31], 0)
            change_percent = (change / prev_close * 100) if prev_close else self._to_float(fields[32], 0)
            result[symbol] = {
                "symbol": symbol,
                "name": name,
                "price": price,
                "change": round(change, 4),
                "change_percent": round(change_percent, 4),
                "volume": volume,
                "high": high,
                "low": low,
                "quote_timestamp": timestamp,
                "quote_source": "direct_tencent",
            }
        return result

    def _fetch_direct_sina_quotes(self, market_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        started = time.time()
        quotes: Dict[str, Dict[str, Any]] = {}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn",
        }
        try:
            for batch in self._chunked(market_symbols, self.quote_batch_size):
                url = f"https://hq.sinajs.cn/list={','.join(batch)}"
                text = self._get_http_text(url, headers=headers)
                quotes.update(self._parse_sina_direct_batch(text))
            self._record_source_health(
                "direct_sina",
                success=True,
                latency_ms=(time.time() - started) * 1000,
                item_count=len(quotes),
            )
            return quotes
        except Exception as exc:
            self._record_source_health(
                "direct_sina",
                success=False,
                latency_ms=(time.time() - started) * 1000,
                error=str(exc),
                item_count=len(quotes),
            )
            raise

    def _fetch_direct_tencent_quotes(self, market_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        started = time.time()
        quotes: Dict[str, Dict[str, Any]] = {}
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            for batch in self._chunked(market_symbols, self.quote_batch_size):
                url = f"https://qt.gtimg.cn/q={','.join(batch)}"
                text = self._get_http_text(url, headers=headers)
                quotes.update(self._parse_tencent_direct_batch(text))
            self._record_source_health(
                "direct_tencent",
                success=True,
                latency_ms=(time.time() - started) * 1000,
                item_count=len(quotes),
            )
            return quotes
        except Exception as exc:
            self._record_source_health(
                "direct_tencent",
                success=False,
                latency_ms=(time.time() - started) * 1000,
                error=str(exc),
                item_count=len(quotes),
            )
            raise

    def _fetch_single_direct_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        market_symbol = self._to_market_symbol(symbol)
        for source_name, fetcher in (
            ("direct_sina", self._fetch_direct_sina_quotes),
            ("direct_tencent", self._fetch_direct_tencent_quotes),
        ):
            try:
                quotes = fetcher([market_symbol])
                quote = quotes.get(self._normalize_symbol(symbol))
                if quote and quote.get("price", 0) > 0:
                    return quote
            except Exception:
                self._record_source_health(source_name, success=False, error=f"{source_name} single quote failed")
        return None

    def _merge_quotes(
        self,
        stocks: List[Dict[str, Any]],
        quotes: Dict[str, Dict[str, Any]],
        *,
        overwrite_name: bool = False,
    ) -> int:
        merged = 0
        for stock in stocks:
            quote = quotes.get(stock["symbol"])
            if not quote:
                continue
            if quote.get("price", 0) > 0:
                stock["price"] = self._to_float(quote.get("price"), stock["price"])
                stock["change"] = self._to_float(quote.get("change"), stock["change"])
                stock["change_percent"] = self._to_float(quote.get("change_percent"), stock["change_percent"])
            if quote.get("volume", 0) > 0:
                stock["volume"] = self._to_int(quote.get("volume"), stock["volume"])
            if overwrite_name and quote.get("name"):
                stock["name"] = str(quote["name"]).strip()
            if quote.get("quote_source"):
                stock["quote_source"] = quote["quote_source"]
            if quote.get("quote_timestamp"):
                stock["quote_timestamp"] = quote["quote_timestamp"]
            merged += 1
        return merged

    def _stocks_from_akshare_df(self, stock_df: Any) -> List[Dict[str, Any]]:
        stocks: List[Dict[str, Any]] = []
        for row in stock_df.to_dict("records"):
            parsed = self._parse_stock_row(row)
            if parsed is not None:
                stocks.append(parsed)
        return stocks

    def _fetch_eastmoney_direct_spot(self) -> tuple[List[Dict[str, Any]], str]:
        started = time.time()
        params_base = {
            "pz": self.eastmoney_page_size,
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": "f12,f14,f2,f3,f4,f5,f6,f20",
        }
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
        last_error: Optional[Exception] = None

        for url in self.eastmoney_direct_hosts:
            stocks: List[Dict[str, Any]] = []
            page = 1
            try:
                while page <= self.eastmoney_max_pages:
                    payload = self._get_http_json(
                        url,
                        params={**params_base, "pn": page},
                        headers=headers,
                        timeout=self.eastmoney_request_timeout,
                    )
                    items = (payload.get("data") or {}).get("diff") or []
                    if not items:
                        break
                    for item in items:
                        symbol = self._normalize_symbol(item.get("f12"))
                        name = str(item.get("f14") or "").strip()
                        price = self._to_float(item.get("f2"), 0)
                        if not symbol or not name or price <= 0:
                            continue
                        stocks.append(
                            {
                                "symbol": symbol,
                                "name": name,
                                "price": price,
                                "change": self._to_float(item.get("f4"), 0),
                                "change_percent": self._to_float(item.get("f3"), 0),
                                "volume": self._to_int(item.get("f5"), 0),
                                "market_cap": self._to_float(item.get("f20"), 0),
                            }
                        )
                    if len(items) < self.eastmoney_page_size:
                        break
                    page += 1
                    time.sleep(0.12)

                if len(stocks) >= self.min_baseline_universe:
                    self._record_source_health(
                        "eastmoney_direct",
                        success=True,
                        latency_ms=(time.time() - started) * 1000,
                        item_count=len(stocks),
                        extra={"pages": page, "host": url},
                    )
                    return stocks, self._now_iso()
            except Exception as exc:
                last_error = exc
                self._record_source_health(
                    "eastmoney_direct",
                    success=False,
                    latency_ms=(time.time() - started) * 1000,
                    error=str(exc),
                    extra={"host": url},
                )

        raise last_error if last_error is not None else Exception("Eastmoney direct source returned no usable stocks")

    def _fetch_baseline_universe(self) -> tuple[List[Dict[str, Any]], str, str]:
        import akshare as ak

        candidates: List[tuple[int, str, List[Dict[str, Any]], str]] = []
        errors: List[str] = []

        try:
            stocks, quote_timestamp = self._fetch_eastmoney_direct_spot()
            if stocks:
                candidates.append((len(stocks), "eastmoney_direct", stocks, quote_timestamp))
        except Exception as exc:
            errors.append(f"eastmoney_direct: {exc}")

        for ak_source in ("akshare_sina", "akshare_em"):
            try:
                stock_df = self._fetch_spot_df_with_retry(ak, ak_source)
                stocks = self._stocks_from_akshare_df(stock_df)
                if stocks:
                    candidates.append(
                        (len(stocks), ak_source, stocks, self._extract_quote_timestamp(stock_df))
                    )
            except Exception as exc:
                errors.append(f"{ak_source}: {exc}")

        if not candidates:
            raise Exception("No stock universe available: " + " | ".join(errors))

        candidates.sort(key=lambda item: item[0], reverse=True)
        count, baseline_source, stocks, quote_timestamp = candidates[0]
        if count < self.min_baseline_universe:
            errors.append(
                f"baseline universe below expected size ({count} < {self.min_baseline_universe})"
            )
        return stocks, quote_timestamp, baseline_source

    def _fetch_aggregate_realtime_payload(self) -> Dict[str, Any]:
        try:
            stocks, quote_timestamp, baseline_source = self._fetch_baseline_universe()
        except Exception as exc:
            raise Exception(str(exc)) from exc

        if not stocks:
            raise Exception("No stock universe available for aggregate realtime fetch")

        market_symbols = [self._to_market_symbol(stock["symbol"]) for stock in stocks]
        source_summary: Dict[str, Any] = {
            "mode": "aggregate_realtime",
            "baseline_source": baseline_source,
            "baseline_count": len(stocks),
            "validated_sources": [],
            "validated_symbols": 0,
        }

        sina_quotes: Dict[str, Dict[str, Any]] = {}
        tencent_quotes: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []

        try:
            sina_quotes = self._fetch_direct_sina_quotes(market_symbols)
            validated = self._merge_quotes(stocks, sina_quotes, overwrite_name=True)
            if validated > 0:
                source_summary["validated_sources"].append("direct_sina")
                source_summary["validated_symbols"] += validated
                quote_timestamp = max(
                    [quote_timestamp] + [q.get("quote_timestamp", "") for q in sina_quotes.values() if q.get("quote_timestamp")]
                )
        except Exception as exc:
            errors.append(f"direct_sina: {exc}")

        if len(sina_quotes) < len(stocks):
            missing_market_symbols = [
                self._to_market_symbol(stock["symbol"])
                for stock in stocks
                if stock["symbol"] not in sina_quotes
            ]
            if missing_market_symbols:
                try:
                    tencent_quotes = self._fetch_direct_tencent_quotes(missing_market_symbols)
                    validated = self._merge_quotes(stocks, tencent_quotes, overwrite_name=False)
                    if validated > 0:
                        source_summary["validated_sources"].append("direct_tencent")
                        source_summary["validated_symbols"] += validated
                        quote_timestamp = max(
                            [quote_timestamp]
                            + [q.get("quote_timestamp", "") for q in tencent_quotes.values() if q.get("quote_timestamp")]
                        )
                except Exception as exc:
                    errors.append(f"direct_tencent: {exc}")

        source_summary["coverage_ratio"] = round(
            (source_summary["validated_symbols"] / len(stocks)) if stocks else 0.0,
            4,
        )
        if len(stocks) < self.min_baseline_universe:
            source_summary["warnings"] = source_summary.get("warnings", []) + [
                f"baseline universe below expected size ({len(stocks)} < {self.min_baseline_universe})"
            ]
        if errors:
            source_summary["warnings"] = source_summary.get("warnings", []) + errors

        return {
            "stocks": stocks,
            "source": "aggregate_realtime",
            "fetched_at": self._now_iso(),
            "quote_timestamp": quote_timestamp,
            "source_summary": source_summary,
        }

    def _fetch_live_payload(self) -> Dict[str, Any]:
        import akshare as ak

        errors: List[str] = []
        for source in self._candidate_sources():
            try:
                if source == "aggregate_realtime":
                    payload = self._fetch_aggregate_realtime_payload()
                elif source == "direct_sina":
                    payload = self._fetch_aggregate_realtime_payload()
                    payload["source"] = "aggregate_realtime"
                elif source == "direct_tencent":
                    payload = self._fetch_aggregate_realtime_payload()
                    payload["source"] = "aggregate_realtime"
                else:
                    stock_df = self._fetch_spot_df_with_retry(ak, source)
                    stocks: List[Dict[str, Any]] = []
                    for row in stock_df.to_dict("records"):
                        parsed = self._parse_stock_row(row)
                        if parsed is not None:
                            stocks.append(parsed)
                    if not stocks:
                        raise Exception("Live source returned no usable stocks")
                    payload = {
                        "stocks": stocks,
                        "source": source,
                        "fetched_at": self._now_iso(),
                        "quote_timestamp": self._extract_quote_timestamp(stock_df),
                        "source_summary": {
                            "mode": source,
                            "baseline_source": source,
                            "baseline_count": len(stocks),
                            "validated_sources": [],
                            "validated_symbols": 0,
                            "coverage_ratio": 0.0,
                        },
                    }
                self._record_refresh_attempt(success=True, source=payload["source"])
                return payload
            except Exception as exc:
                errors.append(f"{source}: {exc}")
                self._record_refresh_attempt(success=False, source=source, error=str(exc))

        raise Exception("All live stock sources failed: " + " | ".join(errors))

    def _limit_payload(self, payload: Dict[str, Any], limit: int) -> Dict[str, Any]:
        if limit <= 0:
            return payload
        data = payload["data"]
        stocks = list(data["stocks"])[:limit]
        freshness = data["freshness"]
        return self._build_stocks_payload(
            stocks,
            data["total"],
            data["last_update"],
            source=freshness["source"],
            cache_origin=freshness["cache_origin"],
            is_live=freshness["is_live"],
            last_error=freshness.get("last_error") or None,
            quote_timestamp=freshness.get("quote_timestamp", ""),
            source_summary=freshness.get("source_summary") or {},
        )

    def _build_payload_from_disk_cache(
        self,
        disk_cached: Dict[str, Any],
        last_error: str,
        *,
        refresh_skipped: bool = False,
    ) -> Dict[str, Any]:
        stocks = disk_cached.get("stocks", [])
        total = int(disk_cached.get("total", len(stocks)))
        last_update = str(disk_cached.get("last_update", self._now_iso()))
        source = str(disk_cached.get("source") or "disk_cache")
        quote_timestamp = str(disk_cached.get("quote_timestamp") or "")
        source_summary = disk_cached.get("source_summary") or {}
        return self._build_stocks_payload(
            stocks,
            total,
            last_update,
            source=source,
            cache_origin="disk",
            is_live=False,
            last_error=last_error,
            quote_timestamp=quote_timestamp,
            source_summary=source_summary,
            refresh_skipped=refresh_skipped,
        )

    def get_stocks(self, limit: int = 0, force_refresh: bool = True) -> Dict[str, Any]:
        limit = int(limit or 0)
        cache_key = "stocks_list_full"
        trading_date = self._effective_trading_date()
        should_fetch_live = self._should_fetch_live(force_refresh)

        if self.trading_session_aware and not should_fetch_live:
            cached_payload = self._get_session_memory_cache(cache_key, trading_date)
            if cached_payload is not None:
                return self._limit_payload(cached_payload, limit)

            disk_cached = self._get_trading_day_snapshot(trading_date)
            if disk_cached is not None:
                payload = self._build_payload_from_disk_cache(
                    disk_cached,
                    f"Using {trading_date} market snapshot outside trading session",
                    refresh_skipped=True,
                )
                self._set_session_memory_cache(cache_key, trading_date, payload)
                self._last_live_stocks = list(disk_cached.get("stocks", []))
                return self._limit_payload(payload, limit)

        if self.trading_session_aware and should_fetch_live and not force_refresh:
            cached_payload = self._get_session_memory_cache(cache_key, trading_date)
            if cached_payload is not None:
                return self._limit_payload(cached_payload, limit)

        if not self.live_only_market_data and not force_refresh:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return self._limit_payload(cached, limit)

        if not self.has_real_data:
            raise Exception("Real data mode is disabled")

        try:
            live = self._fetch_live_payload()
        except Exception as exc:
            disk_cached = self._read_stocks_disk_cache()
            if disk_cached and isinstance(disk_cached.get("stocks"), list) and disk_cached["stocks"]:
                cache_age = time.time() - float(disk_cached.get("timestamp", 0) or 0)
                if cache_age <= self.max_stale_fallback:
                    payload = self._build_payload_from_disk_cache(
                        disk_cached,
                        f"Live fetch failed; showing last successful snapshot ({int(cache_age)}s old): {exc}",
                    )
                    if self.trading_session_aware:
                        self._set_session_memory_cache(cache_key, trading_date, payload)
                    return self._limit_payload(payload, limit)
            raise

        self._write_stocks_disk_cache(
            live["stocks"],
            source=live["source"],
            fetched_at=live["fetched_at"],
            quote_timestamp=live["quote_timestamp"],
            source_summary=live.get("source_summary"),
        )
        payload = self._build_stocks_payload(
            live["stocks"],
            len(live["stocks"]),
            live["fetched_at"],
            source=live["source"],
            cache_origin="live",
            is_live=True,
            quote_timestamp=live["quote_timestamp"],
            source_summary=live.get("source_summary"),
        )
        if self.trading_session_aware:
            self._set_session_memory_cache(cache_key, trading_date, payload)
        elif not self.live_only_market_data:
            self._set_cache(cache_key, payload)
            self.cache.pop("market_overview", None)
        self._last_live_stocks = list(live["stocks"])
        return self._limit_payload(payload, limit)

    def _find_from_cached_stock_list(self, symbol: str) -> Optional[Dict[str, Any]]:
        if self.live_only_market_data and self._last_live_stocks:
            for item in self._last_live_stocks:
                if self._symbols_match(item.get("symbol"), symbol):
                    return item

        cached_entry = self.cache.get("stocks_list_full", {})
        payload = cached_entry.get("data")
        if not payload:
            return None
        cached_list = payload.get("data", {}) if isinstance(payload, dict) else {}
        stocks = cached_list.get("stocks", [])
        for item in stocks:
            if self._symbols_match(item.get("symbol"), symbol):
                return item
        return None

    def get_stock_detail(self, symbol: str) -> Dict[str, Any]:
        if self.live_only_market_data:
            return self._get_real_stock_detail(symbol)

        cache_key = f"stock_detail_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        detail = self._get_real_stock_detail(symbol)
        self._set_cache(cache_key, detail)
        return detail

    def _get_real_stock_detail(self, symbol: str) -> Dict[str, Any]:
        import akshare as ak

        symbol = self._normalize_symbol(symbol)
        if not symbol:
            raise Exception("Stock symbol is required")

        base = self._find_from_cached_stock_list(symbol)
        quote_source = "stocks_cache" if base is not None else ""
        quote_timestamp = ""
        errors: List[str] = []

        if base is None:
            try:
                self.get_stocks(limit=0, force_refresh=True)
                base = self._find_from_cached_stock_list(symbol)
                if base is not None:
                    quote_source = "live_market_snapshot"
            except Exception as exc:
                errors.append(f"live_market_snapshot: {exc}")

        direct_quote = self._fetch_single_direct_quote(symbol)
        if direct_quote:
            if base is None:
                base = {
                    "symbol": symbol,
                    "name": str(direct_quote.get("name") or symbol),
                    "price": self._to_float(direct_quote.get("price"), 0),
                    "change": self._to_float(direct_quote.get("change"), 0),
                    "change_percent": self._to_float(direct_quote.get("change_percent"), 0),
                    "volume": self._to_int(direct_quote.get("volume"), 0),
                    "market_cap": 0.0,
                }
            else:
                if direct_quote.get("price", 0) > 0:
                    base["price"] = self._to_float(direct_quote.get("price"), base["price"])
                    base["change"] = self._to_float(direct_quote.get("change"), base["change"])
                    base["change_percent"] = self._to_float(
                        direct_quote.get("change_percent"),
                        base["change_percent"],
                    )
                if direct_quote.get("volume", 0) > 0:
                    base["volume"] = self._to_int(direct_quote.get("volume"), base["volume"])
                if direct_quote.get("name"):
                    base["name"] = str(direct_quote["name"]).strip()
            quote_source = str(direct_quote.get("quote_source") or quote_source)
            quote_timestamp = str(direct_quote.get("quote_timestamp") or "")

        if base is None:
            for source in ("akshare_sina", "akshare_em"):
                try:
                    stock_df = self._fetch_spot_df_with_retry(ak, source)
                    symbol_column = next(
                        (column for column in self._column_aliases["symbol"] if column in stock_df.columns),
                        self._column_aliases["symbol"][0],
                    )
                    stock_row = stock_df[
                        stock_df[symbol_column].astype(str).map(self._normalize_symbol) == symbol
                    ]
                    if stock_row.empty:
                        continue
                    parsed = self._parse_stock_row(stock_row.iloc[0].to_dict())
                    if parsed is None:
                        continue
                    base = parsed
                    quote_source = source
                    quote_timestamp = self._extract_quote_timestamp(stock_df)
                    break
                except Exception as exc:
                    errors.append(f"{source}: {exc}")

        if base is None:
            raise Exception(f"Stock {symbol} not found. Source errors: {' | '.join(errors)}")

        history: List[Dict[str, Any]] = []
        history_error = None
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
            history_df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="",
            )
            if not history_df.empty:
                for _, row in history_df.tail(120).iterrows():
                    date_value = self._pick_value(row, "date")
                    date_text = date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value)
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
        except Exception as exc:
            history_error = str(exc)
            history = []

        if not history:
            try:
                daily_df = ak.stock_zh_a_daily(symbol=self._to_market_symbol(symbol), adjust="")
                if daily_df is not None and not daily_df.empty:
                    for _, row in daily_df.tail(120).iterrows():
                        date_value = row.get("date")
                        date_text = date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value)
                        history.append(
                            {
                                "date": date_text,
                                "open": self._to_float(row.get("open", 0)),
                                "high": self._to_float(row.get("high", 0)),
                                "low": self._to_float(row.get("low", 0)),
                                "close": self._to_float(row.get("close", 0)),
                                "volume": self._to_int(row.get("volume", 0)),
                            }
                        )
                    history_error = None
            except Exception as exc:
                history_error = f"{history_error} | fallback: {exc}" if history_error else str(exc)

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
            "timestamp": self._now_iso(),
            "freshness": {
                "quote_source": quote_source,
                "quote_timestamp": quote_timestamp,
                "history_points": len(history),
                "history_error": history_error or "",
                "source_health": dict(self.source_health),
            },
        }

    def get_market_overview(self, force_refresh: bool = True) -> Dict[str, Any]:
        cache_key = "market_overview"
        if not self.live_only_market_data and not force_refresh:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return cached

        stocks_data = self.get_stocks(limit=0, force_refresh=force_refresh)
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
            "timestamp": self._now_iso(),
            "freshness": dict(stocks_data["data"].get("freshness") or {}),
        }
        try:
            from flask_services.feature_history_store import feature_history_store

            trading_date = self._effective_trading_date()
            breadth = (rising_stocks - falling_stocks) / max(1, total_stocks)
            feature_history_store.record_market_breadth(trading_date, float(breadth))
        except Exception:
            pass
        if not self.live_only_market_data:
            self._set_cache(cache_key, overview)
        return overview

    def clear_cache(self) -> None:
        self.cache.clear()


data_service = DataService()
