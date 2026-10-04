"""
Prediction service for stock forecasting and backtesting.
"""

import logging
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

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout = 3600
        self._trained_models: Dict[Tuple[str, int, float, str], float] = {}
        self._history_cache: Dict[str, Dict[str, Any]] = {}
        self.predict_timeout_seconds = 180
        self._model_lock = threading.Lock()
        self._storage_lock = threading.RLock()
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = data_dir / "prediction_runs.json"
        self._init_prediction_service()

    def _init_prediction_service(self) -> None:
        from core.akshare_data_collector import AKShareDataCollector
        from core.improved_predictor import ImprovedPredictor

        self.predictor = ImprovedPredictor(learn_weights=True)
        self.collector = AKShareDataCollector()
        self.has_real_predictor = True
        print("Prediction service initialized with ImprovedPredictor (weight learning + LSTM enabled)")

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
            try:
                hist_df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
                records = self._history_df_to_records(code, hist_df)
            except Exception:
                records = []

        if not records:
            try:
                market_symbol = self._to_market_symbol(code)
                daily_df = ak.stock_zh_a_daily(symbol=market_symbol, adjust="qfq")
                records = self._history_df_to_records(code, daily_df.tail(1200))
            except Exception:
                records = []

        if records:
            self._history_cache[code] = {"timestamp": time.time(), "data": list(records)}
        return records

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

        if len(df) < min_rows:
            raise ValueError(f"Insufficient history for {normalized_symbol}: {len(df)} rows")

        return df

    @staticmethod
    def _truncate_df_as_of(df: pd.DataFrame, as_of_date: Optional[str]) -> pd.DataFrame:
        if not as_of_date or "date" not in df.columns:
            return df
        work = df.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        cutoff = pd.to_datetime(str(as_of_date), errors="coerce")
        if pd.isna(cutoff):
            return df
        trimmed = work[work["date"] <= cutoff].sort_values("date")
        if len(trimmed) < 80:
            raise ValueError(f"Insufficient history as of {as_of_date}: {len(trimmed)} rows")
        return trimmed

    def _ensure_model_ready(
        self,
        symbol: str,
        horizon: int,
        up_threshold: float,
        as_of_date: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> pd.DataFrame:
        as_of_key = str(as_of_date or "")
        key = (symbol, horizon, round(float(up_threshold), 6), as_of_key)
        df = self._load_history_df(symbol)
        df = self._truncate_df_as_of(df, as_of_date)

        last_train = self._trained_models.get(key)
        if last_train is None or (time.time() - last_train) > self.cache_timeout:
            with self._model_lock:
                last_train = self._trained_models.get(key)
                if last_train is None or (time.time() - last_train) > self.cache_timeout:
                    kwargs = {}
                    if task_id:
                        from training_viz.reporter import create_reporter
                        from flask_services.task_manager import task_manager as tm

                        reporter = create_reporter(tm, task_id)
                        model_ids = [
                            f"{l}:{n}"
                            for l, n, _ in self.predictor._iter_all_models()
                        ]
                        reporter.init_models(model_ids)
                        kwargs["progress_callback"] = reporter.on_callback
                    self.predictor.train(
                        df, horizon=horizon, up_threshold=up_threshold, fast=True, **kwargs
                    )
                    self._trained_models[key] = time.time()

        return df

    def predict_stock(
        self,
        symbol: str,
        horizon: int = 5,
        up_threshold: float = 0.02,
        as_of_date: Optional[str] = None,
        record_signal: bool = True,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from flask_services.task_manager import task_manager

        threshold = float(up_threshold)
        as_of_key = str(as_of_date or "")
        cache_key = f"prediction_{symbol}_{horizon}_{threshold:.4f}_{as_of_key}"
        if not as_of_date and cache_key in self.cache:
            cache_time = self.cache[cache_key]["timestamp"]
            if time.time() - cache_time < self.cache_timeout:
                if task_id:
                    task_manager.complete(task_id, self.cache[cache_key]["data"])
                return self.cache[cache_key]["data"]

        if task_id:
            task_manager.update_progress(task_id, 10, "loading_data", f"获取 {symbol} 历史数据...")

        df = self._ensure_model_ready(symbol, horizon, threshold, as_of_date=as_of_date, task_id=task_id)

        if task_id:
            if task_manager.is_cancelled(task_id):
                raise Exception("Task cancelled by user")
            task_manager.update_progress(task_id, 70, "generating_prediction", "Generating prediction...")

        prediction_raw = self.predictor.predict(df, horizon)

        explanation = self.predictor.get_prediction_explanation(prediction_raw)

        result = {
            "symbol": symbol,
            "horizon": horizon,
            "up_threshold": threshold,
            "as_of_date": as_of_date,
            "replay_mode": bool(as_of_date),
            "prediction": prediction_raw["prediction"],
            "raw_prediction": prediction_raw.get("raw_prediction", prediction_raw["prediction"]),
            "direction": "up" if prediction_raw["prediction"] == 1 else "down",
            "raw_direction": "up" if prediction_raw.get("raw_prediction", prediction_raw["prediction"]) == 1 else "down",
            "trade_allowed": bool(prediction_raw.get("trade_allowed", False)),
            "trade_reasons": list(prediction_raw.get("trade_reasons") or []),
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

        if not as_of_date:
            self.cache[cache_key] = {"timestamp": time.time(), "data": result}
            self._append_history_entry("predictions", self._build_prediction_history_entry(result))
        if record_signal and not as_of_date:
            self._record_signal_log(result)
        if task_id:
            task_manager.complete(task_id, result)
        return result

    def _record_signal_log(self, result: Dict[str, Any]) -> None:
        try:
            from flask_services.investment_service import investment_service

            layer = result.get("layer_outputs") or {}
            investment_service.signal_tracker.record(
                symbol=result.get("symbol", ""),
                prediction=int(result.get("prediction", 0)),
                direction=str(result.get("direction", "down")),
                confidence=float(result.get("confidence") or 0),
                horizon=int(result.get("horizon", 5)),
                up_threshold=float(result.get("up_threshold", 0.02)),
                ensemble_up=layer.get("ensemble_up"),
                label_mode=str(result.get("label_mode") or "fixed_horizon"),
            )
            investment_service._resolve_signals_lazy()
        except Exception as exc:
            # Never fatal, but never silent either: a lost sample is lost evidence.
            logger.warning("failed to record signal for %s: %s", result.get("symbol"), exc)

    def backtest_strategy(
        self,
        symbol: str,
        strategy: str = "default",
        horizon: int = 5,
        test_size: float = 0.2,
        up_threshold: float = 0.02,
        min_confidence: float = 0.0,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from flask_services.task_manager import task_manager

        strategy_key = (strategy or "default").lower()
        if strategy_key in {"default", "ensemble", "ml"}:
            strategy_key = "ensemble_ml"

        threshold = float(up_threshold)

        if task_id:
            task_manager.update_progress(task_id, 10, "loading_data", f"获取 {symbol} 历史数据...")

        df = self._load_history_df(symbol)

        if task_id:
            if task_manager.is_cancelled(task_id):
                raise Exception("Task cancelled by user")
            task_manager.update_progress(task_id, 25, "training_models", "执行回测前训练...")

        if task_id:
            if task_manager.is_cancelled(task_id):
                raise Exception("Task cancelled by user")
            task_manager.update_progress(task_id, 40, "running_backtest", "运行回测与 PnL 模拟...")

        backtest_result = self.predictor.backtest(
            df,
            horizon=horizon,
            test_size=test_size,
            strategy=strategy_key,
            up_threshold=threshold,
            min_confidence=float(min_confidence or 0.0),
        )

        if task_id:
            task_manager.update_progress(task_id, 80, "building_result", "构建回测报告...")

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
            "walk_forward": backtest_result.get("results", {}).get("walk_forward", {}),
            "purged_embargo": backtest_result.get("purged_embargo", horizon),
            "train_size": backtest_result.get("train_size"),
            "decision_threshold": backtest_result.get("decision_threshold", 0.5),
            "pnl_backtest": backtest_result.get("pnl_backtest", {}),
            "calibration": backtest_result.get("calibration", {}),
            "timestamp": time.time(),
        }
        self._append_history_entry("backtests", self._build_backtest_history_entry(result))
        if task_id:
            task_manager.complete(task_id, result)
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
