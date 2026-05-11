"""
Prediction service for stock forecasting and backtesting.
"""

import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
        self._model_lock = threading.Lock()
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

    def _fetch_recent_news_items(self, limit: int = 300) -> List[Dict[str, Any]]:
        url = "https://feed.mix.sina.com.cn/api/roll/get"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        }
        page_size = 50
        pages = max(1, min(10, (limit + page_size - 1) // page_size))
        rows: List[Dict[str, Any]] = []
        seen = set()
        for page in range(1, pages + 1):
            params = {
                "pageid": "153",
                "lid": "2510",
                "num": page_size,
                "page": str(page),
                "r": str(datetime.now().timestamp()),
            }
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=10)
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
            result[day] = {
                "sentiment_score": avg,
                "sentiment_confidence": float(conf),
                "positive_ratio": float(pos / n),
                "negative_ratio": float(neg / n),
                "target_match_count": float(hit),
            }
        return result

    def _get_sentiment_snapshot(self, symbol: str) -> Dict[str, Any]:
        key = self._normalize_symbol(symbol)
        cached = self._sentiment_cache.get(key)
        if cached and (time.time() - cached.get("timestamp", 0) < self.sentiment_cache_timeout):
            return cached.get("data", {})

        news_items = self._fetch_recent_news_items(limit=320)
        daily_map = self._build_daily_sentiment_map(news_items)
        market_breadth = 0.0
        try:
            from flask_services.data_service import data_service

            overview = data_service.get_market_overview()
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
        self._sentiment_cache[key] = {"timestamp": time.time(), "data": payload}
        return payload

    def _enrich_with_sentiment_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if "date" not in df.columns:
            return df

        try:
            snap = self._get_sentiment_snapshot(symbol)
        except Exception:
            snap = {"daily_map": {}, "market_breadth": 0.0, "fetched_at": ""}
        daily_map: Dict[str, Dict[str, float]] = snap.get("daily_map", {}) or {}
        market_breadth = float(snap.get("market_breadth", 0.0) or 0.0)

        out = df.copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"]).sort_values("date")

        last_known = {
            "sentiment_score": 0.0,
            "sentiment_confidence": 0.0,
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "target_match_count": 0.0,
        }
        last_day: datetime | None = None

        score_vals = []
        conf_vals = []
        pos_vals = []
        neg_vals = []
        breadth_vals = []
        hit_vals = []
        decay_vals = []
        avail_vals = []

        for dt in out["date"]:
            lag_day = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
            row = daily_map.get(lag_day)
            if row:
                last_known = row
                last_day = dt
                available = 1.0
                decay = 1.0
            else:
                available = 0.0
                if last_day is None:
                    decay = 0.0
                else:
                    gap = max(0, int((dt - last_day).days))
                    decay = float(np.exp(-gap / 7.0))

            score_vals.append(float(last_known.get("sentiment_score", 0.0)))
            conf_vals.append(float(last_known.get("sentiment_confidence", 0.0)))
            pos_vals.append(float(last_known.get("positive_ratio", 0.0)))
            neg_vals.append(float(last_known.get("negative_ratio", 0.0)))
            breadth_vals.append(float(market_breadth))
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
                    self.predictor.train(df, horizon=horizon, up_threshold=up_threshold)
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
            "explanation": explanation,
            "timestamp": time.time(),
        }

        self.cache[cache_key] = {"timestamp": time.time(), "data": result}
        return result

    def backtest_strategy(
        self,
        symbol: str,
        strategy: str = "default",
        horizon: int = 5,
        test_size: float = 0.2,
        up_threshold: float = 0.02,
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
        )

        return {
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
            "timestamp": time.time(),
        }

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

    def get_prediction_history(self, symbol: str) -> List[Dict[str, Any]]:
        return []


prediction_service = PredictionService()
