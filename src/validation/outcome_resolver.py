"""Resolve pending signal outcomes from historical price data."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

import pandas as pd

from validation.signal_tracker import SignalTracker
from validation.triple_barrier import label_triple_barrier


PriceLoader = Callable[[str], pd.DataFrame]


class OutcomeResolver:
    def __init__(
        self,
        signal_tracker: SignalTracker,
        price_loader: PriceLoader,
        label_mode: str = "fixed_horizon",
    ) -> None:
        self.signal_tracker = signal_tracker
        self._price_loader = price_loader
        self.label_mode = label_mode

    def resolve_pending(self, label_mode: Optional[str] = None) -> int:
        mode = label_mode or self.label_mode
        updated = 0
        with self.signal_tracker._lock:
            payload = self.signal_tracker._load()
            for entry in payload.get("logs", []):
                if entry.get("outcome_resolved"):
                    continue
                sym = str(entry.get("symbol", "")).strip()
                if not sym:
                    continue
                try:
                    df = self._price_loader(sym)
                except Exception:
                    continue
                result = self._compute_outcome(df, entry, mode)
                if result is None:
                    continue
                entry["outcome_return"] = float(result["return"])
                entry["outcome_resolved"] = True
                entry["label_mode"] = mode
                entry["barrier_hit"] = result.get("barrier")
                pred = int(entry.get("prediction", 0))
                entry["outcome_correct"] = bool(
                    (pred == 1 and result["return"] > float(entry.get("up_threshold", 0.02)))
                    or (pred == 0 and result["return"] <= float(entry.get("up_threshold", 0.02)))
                )
                updated += 1
            if updated:
                self.signal_tracker._save(payload)
        return updated

    def _compute_outcome(
        self,
        df: pd.DataFrame,
        entry: Dict[str, Any],
        mode: str,
    ) -> Optional[Dict[str, Any]]:
        work = df.copy()
        if "date" in work.columns:
            work["date"] = pd.to_datetime(work["date"], errors="coerce")
            work = work.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        else:
            work = work.reset_index(drop=True)

        if len(work) < 2:
            return None

        horizon = int(entry.get("horizon", 5))
        up_threshold = float(entry.get("up_threshold", 0.02))
        recorded_at = float(entry.get("recorded_at", 0))
        if recorded_at > 0 and "date" in work.columns:
            recorded_dt = datetime.fromtimestamp(recorded_at)
            idx = work["date"].searchsorted(recorded_dt, side="right") - 1
            entry_idx = max(0, min(int(idx), len(work) - 1))
        else:
            entry_idx = max(0, len(work) - horizon - 1)

        entry_price = float(work.iloc[entry_idx]["close_price"])
        if entry_price <= 0:
            return None

        if mode == "triple_barrier":
            stop_loss = float(entry.get("stop_loss_pct", up_threshold))
            path = work.iloc[entry_idx + 1 : entry_idx + 1 + horizon]
            if path.empty:
                return None
            return label_triple_barrier(
                entry_price=entry_price,
                closes=path["close_price"].astype(float).tolist(),
                up_threshold=up_threshold,
                stop_loss_pct=stop_loss,
            )

        exit_idx = entry_idx + horizon
        if exit_idx >= len(work):
            return None
        exit_price = float(work.iloc[exit_idx]["close_price"])
        ret = exit_price / entry_price - 1.0
        return {"return": ret, "barrier": "time"}
