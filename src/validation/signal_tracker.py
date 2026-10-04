"""Track prediction signals and fill outcomes after the horizon elapses."""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SignalTracker:
    def __init__(self, storage_path: Optional[Path] = None) -> None:
        data_dir = Path(__file__).resolve().parents[2] / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._file = storage_path or (data_dir / "signal_logs.json")
        self._lock = threading.RLock()

    def _load(self) -> Dict[str, Any]:
        if not self._file.exists():
            return {"logs": [], "next_id": 1}
        try:
            payload = json.loads(self._file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return {"logs": [], "next_id": 1}
            logs = payload.get("logs")
            next_id = payload.get("next_id", 1)
            return {
                "logs": logs if isinstance(logs, list) else [],
                "next_id": int(next_id) if isinstance(next_id, int) else 1,
            }
        except Exception:
            return {"logs": [], "next_id": 1}

    def _save(self, payload: Dict[str, Any]) -> None:
        self._file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def record(
        self,
        symbol: str,
        prediction: int,
        direction: str,
        confidence: float,
        horizon: int,
        up_threshold: float,
        ensemble_up: Optional[float] = None,
        user_id: Optional[int] = None,
        label_mode: str = "fixed_horizon",
    ) -> str:
        """Record one prediction signal.

        Idempotent per (symbol, horizon, calendar day) while unresolved: repeated
        predictions served from cache would otherwise inflate the live sample.
        Returns the id of the existing entry when the call is a no-op.
        """
        with self._lock:
            payload = self._load()
            symbol = str(symbol).strip()
            today = datetime.now().strftime("%Y-%m-%d")
            for existing in payload.get("logs", []):
                same_key = (
                    str(existing.get("symbol", "")).strip() == symbol
                    and int(existing.get("horizon", 0)) == int(horizon)
                    and str(existing.get("recorded_date", ""))[:10] == today
                )
                if same_key and not existing.get("outcome_resolved"):
                    return str(existing.get("id"))
            log_id = str(uuid.uuid4())
            entry = {
                "id": log_id,
                "symbol": symbol,
                "label_mode": label_mode,
                "prediction": int(prediction),
                "direction": direction,
                "confidence": float(confidence),
                "horizon": int(horizon),
                "up_threshold": float(up_threshold),
                "ensemble_up": float(ensemble_up) if ensemble_up is not None else None,
                "user_id": user_id,
                "recorded_at": time.time(),
                "recorded_date": datetime.now().isoformat(),
                "outcome_return": None,
                "outcome_resolved": False,
                "outcome_correct": None,
            }
            payload["logs"].append(entry)
            payload["next_id"] = int(payload.get("next_id", 1)) + 1
            if len(payload["logs"]) > 5000:
                payload["logs"] = payload["logs"][-5000:]
            self._save(payload)
            return log_id

    def resolve_outcomes(
        self,
        price_lookup: Dict[str, Dict[str, float]],
    ) -> int:
        """Fill outcome_return where price_lookup[symbol] has close_at_record and close_after_horizon."""
        updated = 0
        with self._lock:
            payload = self._load()
            for entry in payload["logs"]:
                if entry.get("outcome_resolved"):
                    continue
                symbol = entry.get("symbol")
                prices = price_lookup.get(symbol) if symbol else None
                if not prices:
                    continue
                ret = prices.get("outcome_return")
                if ret is None:
                    continue
                entry["outcome_return"] = float(ret)
                entry["outcome_resolved"] = True
                pred = int(entry.get("prediction", 0))
                entry["outcome_correct"] = bool(
                    (pred == 1 and ret > float(entry.get("up_threshold", 0.02)))
                    or (pred == 0 and ret <= float(entry.get("up_threshold", 0.02)))
                )
                updated += 1
            if updated:
                self._save(payload)
        return updated

    def get_stats(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        symbol = str(symbol).strip()
        with self._lock:
            payload = self._load()
            rows = [
                x
                for x in payload.get("logs", [])
                if str(x.get("symbol")) == symbol and x.get("outcome_resolved")
            ]
        rows = sorted(rows, key=lambda x: x.get("recorded_at", 0), reverse=True)[:limit]
        if not rows:
            return {
                "symbol": symbol,
                "samples": 0,
                "resolved_samples": 0,
                "accuracy": 0.0,
                "avg_return": 0.0,
                "bullish_samples": 0,
                "bearish_samples": 0,
                "label_mode": "fixed_horizon",
                "barrier_stats": {"counts": {"upper": 0, "lower": 0, "time": 0}},
                "recent": [],
            }

        correct = sum(1 for r in rows if r.get("outcome_correct"))
        returns = [float(r["outcome_return"]) for r in rows if r.get("outcome_return") is not None]
        bullish = sum(1 for r in rows if int(r.get("prediction", 0)) == 1)
        label_mode = str(rows[0].get("label_mode") or "fixed_horizon")
        barrier_counts = {"upper": 0, "lower": 0, "time": 0}
        for r in rows:
            b = str(r.get("barrier_hit") or "time")
            if b in barrier_counts:
                barrier_counts[b] += 1

        return {
            "symbol": symbol,
            "samples": len(rows),
            "resolved_samples": len(rows),
            "accuracy": float(correct / len(rows)) if rows else 0.0,
            "avg_return": float(sum(returns) / len(returns)) if returns else 0.0,
            "bullish_samples": bullish,
            "bearish_samples": len(rows) - bullish,
            "label_mode": label_mode,
            "barrier_stats": {
                "counts": barrier_counts,
                "upper_pct": barrier_counts["upper"] / len(rows),
                "lower_pct": barrier_counts["lower"] / len(rows),
                "time_pct": barrier_counts["time"] / len(rows),
            },
            "recent": rows[:10],
        }

    def list_recent_for_symbols(self, symbols: List[str], limit_per_symbol: int = 1) -> List[Dict[str, Any]]:
        symbols_set = {str(s).strip() for s in symbols}
        with self._lock:
            payload = self._load()
            logs = payload.get("logs", [])
        out: List[Dict[str, Any]] = []
        for sym in symbols_set:
            sym_logs = [x for x in logs if str(x.get("symbol")) == sym]
            sym_logs.sort(key=lambda x: x.get("recorded_at", 0), reverse=True)
            if sym_logs:
                out.append(sym_logs[0])
        return out
