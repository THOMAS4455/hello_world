"""
Prediction service for stock forecasting and backtesting.
"""

import sys
import time
import threading
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class PredictionService:
    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout = 3600
        self._trained_models: Dict[Tuple[str, int, float], float] = {}
        self._history_cache: Dict[str, Dict[str, Any]] = {}
        self._sentiment_cache: Dict[str, Dict[str, Any]] = {}
        self.sentiment_cache_timeout = 1800
        self.predict_timeout_seconds = 180
        self._market_sentiment_cache_key = "__market__"
        self._model_lock = threading.Lock()
        self._storage_lock = threading.RLock()
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = data_dir / "prediction_runs.json"
        self.positive_words = {
            "上涨",
            "反弹",
            "走强",
            "利好",
            "回暖",
            "新高",
            "突破",
            "增持",
            "增长",
            "修复",
            "改善",
        }
        self.negative_words = {
            "下跌",
            "走弱",
            "利空",
            "回落",
            "新低",
            "跌破",
            "减持",
            "风险",
            "承压",
            "担忧",
            "波动",
        }
        self._init_prediction_service()

    def _init_prediction_service(self) -> None:
        from core.akshare_data_collector import AKShareDataCollector
        from core.improved_predictor import ImprovedPredictor

        self.predictor = ImprovedPredictor()
        self.collector = AKShareDataCollector()
        self.has_real_predictor = True
        print("Prediction service initialized")

    def _default_history_payload(self) -> Dict[str, Any]:
        return {"predictions": [], "backtests": []}

    def _load_history_payload(self) -> Dict[str, Any]:
        if not self._history_file.exists():
            return self._default_history_payload()
        try:
            payload = json.loads(self._history_file.read_text(encoding="utf-8"))
        except Exception:
            return self._default_history_payload()
        if not isinstance(payload, dict):
            return self._default_history_payload()
        base = self._default_history_payload()
        for key in ("predictions", "backtests"):
            val = payload.get(key)
            if isinstance(val, list):
                base[key] = val
        return base

    def _save_history_payload(self, payload: Dict[str, Any]) -> None:
        self._history_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_history_entry(self, key: str, entry: Dict[str, Any], max_items: int = 200) -> None:
        with self._storage_lock:
            payload = self._load_history_payload()
            rows = payload.get(key, [])
            if not isinstance(rows, list):
                rows = []
            rows.append(entry)
            payload[key] = rows[-max_items:]
            self._save_history_payload(payload)

    def _build_prediction_history_entry(self, result: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = float(result.get("timestamp") or time.time())
        return {
            "id": str(uuid.uuid4()),
            "symbol": str(result.get("symbol") or ""),
            "horizon": int(result.get("horizon") or 0),
            "up_threshold": float(result.get("up_threshold") or 0.0),
            "prediction": int(result.get("prediction") or 0),
            "direction": str(result.get("direction") or ""),
            "confidence": float(result.get("confidence") or 0.0),
            "timestamp": timestamp,
            "created_at": datetime.fromtimestamp(timestamp).isoformat(),
            "top_models": list(result.get("individual_predictions", {}).keys())[:5],
            "avg_up_probability": float(
                np.mean(
                    [
                        float((value or {}).get("up", 0.0))
                        for value in (result.get("probabilities") or {}).values()
                    ]
                )
                if result.get("probabilities")
                else 0.0
            ),
            "explanation": str(result.get("explanation") or "")[:600],
            "result": result,
        }

    def _build_backtest_history_entry(self, result: Dict[str, Any]) -> Dict[str, Any]:
        walk_forward = result.get("walk_forward") or {}
        timestamp = float(result.get("timestamp") or time.time())
        return {
            "id": str(uuid.uuid4()),
            "symbol": str(result.get("symbol") or ""),
            "strategy": str(result.get("strategy") or ""),
            "horizon": int(result.get("horizon") or 0),
            "up_threshold": float(result.get("up_threshold") or 0.0),
            "test_ratio": float(result.get("test_ratio") or 0.0),
            "baseline_accuracy": float(result.get("baseline_accuracy") or 0.0),
            "improvement": float(result.get("improvement") or 0.0),
            "walk_forward_accuracy": float(walk_forward.get("accuracy") or 0.0),
            "walk_forward_samples": int(walk_forward.get("samples") or 0),
            "timestamp": timestamp,
            "created_at": datetime.fromtimestamp(timestamp).isoformat(),
            "result": result,
        }

    def _read_history_entries(
        self,
        key: str,
        symbol: Optional[str] = None,
        limit: int = 20,
        include_result: bool = False,
    ) -> List[Dict[str, Any]]:
        with self._storage_lock:
            payload = self._load_history_payload()
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            return []
        normalized_symbol = self._normalize_symbol(symbol) if symbol else ""
        items = list(reversed(rows))
        if normalized_symbol:
            items = [item for item in items if self._normalize_symbol(item.get("symbol", "")) == normalized_symbol]
        items = items[: max(1, min(int(limit or 20), 100))]
        if include_result:
            return items
        return [self._strip_history_result(item) for item in items]

    def _strip_history_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        output = dict(item)
        output.pop("result", None)
        return output

    def _read_history_entry(self, key: str, run_id: str) -> Optional[Dict[str, Any]]:
        if not run_id:
            return None
        with self._storage_lock:
            payload = self._load_history_payload()
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            return None
        for item in reversed(rows):
            if str(item.get("id") or "") == str(run_id):
                return item
        return None

    def _normalize_symbol(self, symbol: str) -> str:
        code = "".join(ch for ch in str(symbol or "").strip() if ch.isdigit())
        return code or str(symbol or "").strip()

    def _to_market_symbol(self, symbol: str) -> str:
        code = self._normalize_symbol(symbol)
        if code.startswith(("sh", "sz", "bj")):
            return code
        if code.startswith("6"):
            return f"sh{code}"
        if code.startswith(("0", "3")):
            return f"sz{code}"
        if code.startswith(("4", "8", "9")):
            return f"bj{code}"
        return f"sz{code}"

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if pd.isna(value):
                return default
        except Exception:
            pass
        try:
            return float(value)
        except Exception:
            return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            if pd.isna(value):
                return default
        except Exception:
            pass
        try:
            return int(float(value))
        except Exception:
            return default

    def _history_df_to_records(self, symbol: str, history_df: pd.DataFrame) -> List[Dict[str, Any]]:
        if history_df is None or history_df.empty:
            return []

        cols = list(history_df.columns)
        if len(cols) < 6:
            return []

        date_col = cols[0]
        open_col = cols[1]
        close_col = cols[2]
        high_col = cols[3]
        low_col = cols[4]
        volume_col = cols[5]
        turnover_col = cols[10] if len(cols) > 10 else None

        records: List[Dict[str, Any]] = []
        for _, row in history_df.iterrows():
            date_value = row.get(date_col)
            if hasattr(date_value, "strftime"):
                date_text = date_value.strftime("%Y-%m-%d")
            else:
                date_text = str(date_value)
            records.append(
                {
                    "symbol": self._normalize_symbol(symbol),
                    "date": date_text,
                    "open_price": self._safe_float(row.get(open_col)),
                    "high_price": self._safe_float(row.get(high_col)),
                    "low_price": self._safe_float(row.get(low_col)),
                    "close_price": self._safe_float(row.get(close_col)),
                    "volume": self._safe_int(row.get(volume_col)),
                    "turnover_rate": self._safe_float(row.get(turnover_col), 0.0)
                    if turnover_col is not None
                    else 0.0,
                }
            )
        return records

    def _fetch_history_with_retries(self, symbol: str) -> List[Dict[str, Any]]:
        import akshare as ak

        code = self._normalize_symbol(symbol)
        cached = self._history_cache.get(code)
        if cached and (time.time() - cached.get("timestamp", 0) < self.cache_timeout):
            return list(cached.get("data", []))

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=1200)).strftime("%Y%m%d")

        records: List[Dict[str, Any]] = []
        try:
            history_data = self.collector.get_stock_history(code)
            if history_data:
                records = history_data
        except Exception:
            pass

        if not records:
            for adjust in ("", "qfq"):
                try:
                    hist_df = ak.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust=adjust,
                    )
                    records = self._history_df_to_records(code, hist_df)
                    if records:
                        break
                except Exception:
                    continue

        if not records:
            try:
                market_symbol = self._to_market_symbol(code)
                daily_df = ak.stock_zh_a_daily(symbol=market_symbol, adjust="")
                records = self._history_df_to_records(code, daily_df.tail(1200))
            except Exception:
                records = []

        if records:
            self._history_cache[code] = {"timestamp": time.time(), "data": list(records)}
        return records

    def _normalize_news_time(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.isdigit():
            try:
                ts = int(text)
                if ts > 10_000_000_000:
                    ts = ts // 1000
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            except Exception:
                return ""
        try:
            dt = pd.to_datetime(text, errors="coerce")
            if pd.isna(dt):
                return ""
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""

    def _score_news_title(self, title: str) -> float:
        text = str(title or "")
        pos_hits = sum(1 for w in self.positive_words if w in text)
        neg_hits = sum(1 for w in self.negative_words if w in text)
        total = pos_hits + neg_hits
        if total == 0:
            return 0.0
        return float((pos_hits - neg_hits) / total)

    def _fetch_recent_news_items(self, limit: int = 120) -> List[Dict[str, Any]]:
        try:
            from flask_services.market_sentiment_service import MarketSentimentService
            from flask_services.data_service import data_service

            service = MarketSentimentService(data_service)
            items = service._fetch_finance_news(limit=max(20, min(limit, 200)), sources=["akshare", "sina"])
            return [
                {"title": str(item.get("title", "")).strip(), "time": item.get("time") or item.get("published_at")}
                for item in items
                if str(item.get("title", "")).strip()
            ]
        except Exception:
            pass

        url = "https://feed.mix.sina.com.cn/api/roll/get"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Referer": "https://finance.sina.com.cn",
        }
        page_size = 50
        pages = max(1, min(4, (limit + page_size - 1) // page_size))
        rows: List[Dict[str, Any]] = []
        seen = set()
        session = requests.Session()
        session.trust_env = False
        for page in range(1, pages + 1):
            params = {
                "pageid": "153",
                "lid": "2509",
                "num": page_size,
                "page": str(page),
                "r": str(datetime.now().timestamp()),
            }
            try:
                resp = session.get(url, params=params, headers=headers, timeout=10)
            except Exception:
                continue
            if resp.status_code != 200:
                continue
            try:
                payload = resp.json()
            except Exception:
                continue
            items = payload.get("result", {}).get("data", [])
            for item in items:
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "title": title,
                        "time": item.get("ctime"),
                    }
                )
            if len(rows) >= limit:
                break
        return rows[:limit]

    def _build_daily_sentiment_map(self, news_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        by_day: Dict[str, List[float]] = {}
        by_day_pos: Dict[str, int] = {}
        by_day_neg: Dict[str, int] = {}

        for item in news_items:
            day = self._normalize_news_time(item.get("time"))
            if not day:
                continue
            score = self._score_news_title(item.get("title", ""))
            by_day.setdefault(day, []).append(score)
            if score > 0:
                by_day_pos[day] = by_day_pos.get(day, 0) + 1
            elif score < 0:
                by_day_neg[day] = by_day_neg.get(day, 0) + 1

        result: Dict[str, Dict[str, float]] = {}
        for day, scores in by_day.items():
            n = max(1, len(scores))
            avg = float(sum(scores) / n)
            pos = by_day_pos.get(day, 0)
            neg = by_day_neg.get(day, 0)
            hit = pos + neg
            conf = min(1.0, hit / n)
            metrics = {
                "sentiment_score": avg,
                "sentiment_confidence": float(conf),
                "positive_ratio": float(pos / n),
                "negative_ratio": float(neg / n),
                "target_match_count": float(hit),
            }
            result[day] = metrics
            try:
                from flask_services.feature_history_store import feature_history_store

                feature_history_store.record_sentiment_daily(day, metrics)
            except Exception:
                pass
        return result

    def _merge_point_in_time_maps(
        self, live_daily_map: Dict[str, Dict[str, float]]
    ) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
        try:
            from flask_services.feature_history_store import feature_history_store

            sentiment_map = feature_history_store.get_sentiment_map()
            breadth_map = feature_history_store.get_breadth_map()
        except Exception:
            sentiment_map = {}
            breadth_map = {}
        merged_sentiment = {**sentiment_map, **(live_daily_map or {})}
        return merged_sentiment, breadth_map

    def _get_sentiment_snapshot(self, symbol: str) -> Dict[str, Any]:
        cached = self._sentiment_cache.get(self._market_sentiment_cache_key)
        if cached and (time.time() - cached.get("timestamp", 0) < self.sentiment_cache_timeout):
            return cached.get("data", {})

        news_items = self._fetch_recent_news_items(limit=120)
        daily_map = self._build_daily_sentiment_map(news_items)
        market_breadth = 0.0
        try:
            from flask_services.data_service import data_service

            overview = data_service.get_market_overview(force_refresh=False)
            rising = float(overview.get("rising_stocks", 0))
            falling = float(overview.get("falling_stocks", 0))
            total = float(max(1, overview.get("total_stocks", rising + falling)))
            market_breadth = (rising - falling) / total
        except Exception:
            market_breadth = 0.0

        payload = {
            "daily_map": daily_map,
            "market_breadth": float(market_breadth),
            "fetched_at": datetime.now().strftime("%Y-%m-%d"),
        }
        merged_sentiment, breadth_map = self._merge_point_in_time_maps(daily_map)
        payload["daily_map"] = merged_sentiment
        payload["breadth_map"] = breadth_map
        self._sentiment_cache[self._market_sentiment_cache_key] = {"timestamp": time.time(), "data": payload}
        return payload

    def _enrich_with_sentiment_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if "date" not in df.columns:
            return df

        try:
            snap = self._get_sentiment_snapshot(symbol)
        except Exception:
            snap = {"daily_map": {}, "breadth_map": {}, "market_breadth": 0.0, "fetched_at": ""}

        from flask_services.feature_history_store import feature_history_store

        daily_map: Dict[str, Dict[str, float]] = snap.get("daily_map", {}) or {}
        breadth_map: Dict[str, float] = dict(snap.get("breadth_map", {}) or {})
        fetched_at = str(snap.get("fetched_at") or "")[:10]
        live_breadth = float(snap.get("market_breadth", 0.0) or 0.0)
        if fetched_at and live_breadth:
            breadth_map.setdefault(fetched_at, live_breadth)

        out = df.copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"]).sort_values("date")
        trading_days = out["date"].dt.strftime("%Y-%m-%d").tolist()

        last_known = {
            "sentiment_score": 0.0,
            "sentiment_confidence": 0.0,
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "target_match_count": 0.0,
        }
        last_sent_day: datetime | None = None
        last_breadth = 0.0

        score_vals = []
        conf_vals = []
        pos_vals = []
        neg_vals = []
        breadth_vals = []
        hit_vals = []
        decay_vals = []
        avail_vals = []

        for dt in out["date"]:
            day = dt.strftime("%Y-%m-%d")
            lag_day = feature_history_store.prev_trading_day(trading_days, day)
            row = daily_map.get(lag_day) if lag_day else None
            if row:
                last_known = row
                last_sent_day = dt
                available = 1.0
                decay = 1.0
            else:
                available = 0.0
                if last_sent_day is None:
                    decay = 0.0
                else:
                    gap = max(0, int((dt - last_sent_day).days))
                    decay = float(np.exp(-gap / 7.0))

            if lag_day and lag_day in breadth_map:
                last_breadth = float(breadth_map.get(lag_day, 0.0) or 0.0)
            breadth_val = last_breadth if lag_day else 0.0

            score_vals.append(float(last_known.get("sentiment_score", 0.0)))
            conf_vals.append(float(last_known.get("sentiment_confidence", 0.0)))
            pos_vals.append(float(last_known.get("positive_ratio", 0.0)))
            neg_vals.append(float(last_known.get("negative_ratio", 0.0)))
            breadth_vals.append(float(breadth_val))
            hit_vals.append(float(last_known.get("target_match_count", 0.0)))
            decay_vals.append(float(decay))
            avail_vals.append(float(available))

        out["sentiment_score_lag1"] = score_vals
        out["sentiment_confidence_lag1"] = conf_vals
        out["positive_ratio_lag1"] = pos_vals
        out["negative_ratio_lag1"] = neg_vals
        out["market_breadth_lag1"] = breadth_vals
        out["target_match_count_lag1"] = hit_vals
        out["sentiment_decay_lag1"] = decay_vals
        out["sentiment_available"] = avail_vals
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        return out

    def _load_history_df(self, symbol: str, min_rows: int = 80) -> pd.DataFrame:
        normalized_symbol = self._normalize_symbol(symbol)
        history_data = self._fetch_history_with_retries(normalized_symbol)
        if not history_data:
            raise ValueError(f"No historical data for {normalized_symbol}")

        df = pd.DataFrame(history_data)
        if df.empty:
            raise ValueError(f"Empty historical dataframe for {normalized_symbol}")

        required_cols = ["close_price", "volume"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column '{col}' for {normalized_symbol}")

        if "open_price" not in df.columns:
            df["open_price"] = df["close_price"]
        if "high_price" not in df.columns:
            df["high_price"] = df["close_price"]
        if "low_price" not in df.columns:
            df["low_price"] = df["close_price"]
        if "turnover_rate" not in df.columns:
            df["turnover_rate"] = 0.0

        if "date" in df.columns:
            df = df.sort_values("date")

        df = self._enrich_with_sentiment_features(df, normalized_symbol)

        if len(df) < min_rows:
            raise ValueError(f"Insufficient history for {normalized_symbol}: {len(df)} rows")

        return df

    def _ensure_model_ready(self, symbol: str, horizon: int, up_threshold: float) -> pd.DataFrame:
        key = (symbol, horizon, round(float(up_threshold), 6))
        df = self._load_history_df(symbol)

        last_train = self._trained_models.get(key)
        if last_train is None or (time.time() - last_train) > self.cache_timeout:
            with self._model_lock:
                last_train = self._trained_models.get(key)
                if last_train is None or (time.time() - last_train) > self.cache_timeout:
                    self.predictor.train(df, horizon=horizon, up_threshold=up_threshold, fast=True)
                    self._trained_models[key] = time.time()

        return df

    def predict_stock(
        self, symbol: str, horizon: int = 5, up_threshold: float = 0.02
    ) -> Dict[str, Any]:
        threshold = float(up_threshold)
        cache_key = f"prediction_{symbol}_{horizon}_{threshold:.4f}"
        if cache_key in self.cache:
            cache_time = self.cache[cache_key]["timestamp"]
            if time.time() - cache_time < self.cache_timeout:
                return self.cache[cache_key]["data"]

        df = self._ensure_model_ready(symbol, horizon, threshold)
        prediction_raw = self.predictor.predict(df, horizon)
        explanation = self.predictor.get_prediction_explanation(prediction_raw)

        result = {
            "symbol": symbol,
            "horizon": horizon,
            "up_threshold": threshold,
            "prediction": prediction_raw["prediction"],
            "direction": "up" if prediction_raw["prediction"] == 1 else "down",
            "confidence": prediction_raw["confidence"],
            "individual_predictions": prediction_raw["individual_predictions"],
            "probabilities": prediction_raw["probabilities"],
            "model_scores": prediction_raw.get("model_scores", {}),
            "layer_outputs": prediction_raw.get("layer_outputs", {}),
            "decision_threshold": float(prediction_raw.get("decision_threshold", 0.5) or 0.5),
            "calibration_applied": bool(prediction_raw.get("calibration_applied", False)),
            "explanation": explanation,
            "timestamp": time.time(),
        }

        self.cache[cache_key] = {"timestamp": time.time(), "data": result}
        self._append_history_entry("predictions", self._build_prediction_history_entry(result))
        return result

    def backtest_strategy(
        self,
        symbol: str,
        strategy: str = "default",
        horizon: int = 5,
        test_size: float = 0.2,
        up_threshold: float = 0.02,
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        strategy_key = (strategy or "default").lower()
        if strategy_key in {"default", "ensemble", "ml"}:
            strategy_key = "ensemble_ml"

        threshold = float(up_threshold)
        df = self._load_history_df(symbol)

        backtest_result = self.predictor.backtest(
            df,
            horizon=horizon,
            test_size=test_size,
            strategy=strategy_key,
            up_threshold=threshold,
            min_confidence=float(min_confidence or 0.0),
        )

        result = {
            "symbol": symbol,
            "strategy": strategy_key,
            "horizon": horizon,
            "up_threshold": threshold,
            "test_ratio": test_size,
            "period": f"{len(df)} days",
            "results": backtest_result["results"],
            "baseline_accuracy": backtest_result["baseline_accuracy"],
            "improvement": backtest_result["improvement"],
            "feature_importance": backtest_result.get("feature_importance", {}),
            "sentiment_comparison": backtest_result.get("sentiment_comparison", {}),
            "walk_forward": backtest_result.get("results", {}).get("walk_forward", {}),
            "purged_embargo": backtest_result.get("purged_embargo", horizon),
            "train_size": backtest_result.get("train_size"),
            "decision_threshold": backtest_result.get("decision_threshold", 0.5),
            "pnl_backtest": backtest_result.get("pnl_backtest", {}),
            "calibration": backtest_result.get("calibration", {}),
            "timestamp": time.time(),
        }
        self._append_history_entry("backtests", self._build_backtest_history_entry(result))
        return result

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "service_name": "prediction_service",
            "available_models": [
                "baseline:rf",
                "baseline:gb",
                "enhanced:extra_trees",
                "enhanced:log_reg",
                "enhanced:svm",
                "regime:bull/bear/range/high_vol",
                "ensemble_ml",
                "ma_cross",
                "rsi_reversion",
            ],
            "model_layers": [
                "layer1_baseline",
                "layer2_enhanced",
                "layer3_regime",
            ],
            "default_horizon": 5,
            "max_horizon": 30,
            "model_status": "ready",
            "trained_model_count": len(self._trained_models),
        }

    def get_prediction_history(self, symbol: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self._read_history_entries("predictions", symbol, limit)

    def get_backtest_history(self, symbol: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self._read_history_entries("backtests", symbol, limit)

    def get_prediction_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._read_history_entry("predictions", run_id)

    def get_backtest_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._read_history_entry("backtests", run_id)


prediction_service = PredictionService()
