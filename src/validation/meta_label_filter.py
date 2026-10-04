"""Meta-labeling filter: trade_allowed and suggested position size from history + confidence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def compute_meta_score(
    *,
    symbol: str,
    prediction: int,
    confidence: float,
    resolved_logs: List[Dict[str, Any]],
    min_samples: int = 5,
    cutoff_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """Heuristic meta-layer (MVP): rolling accuracy + current confidence."""
    sym_logs = [
        x
        for x in resolved_logs
        if str(x.get("symbol")) == str(symbol).strip() and x.get("outcome_resolved")
    ]
    if cutoff_ts is not None:
        sym_logs = [x for x in sym_logs if float(x.get("recorded_at", 0)) <= cutoff_ts]
    sym_logs = sorted(sym_logs, key=lambda x: x.get("recorded_at", 0), reverse=True)[:50]

    historical_accuracy = 0.5
    if len(sym_logs) >= min_samples:
        correct = sum(1 for x in sym_logs if x.get("outcome_correct"))
        historical_accuracy = correct / len(sym_logs)

    conf = max(0.0, min(1.0, float(confidence)))
    meta_score = 0.6 * historical_accuracy + 0.4 * conf

    trade_allowed = int(prediction) == 1 and meta_score >= 0.52
    if int(prediction) != 1:
        trade_allowed = False

    suggested_size_pct = 0.0
    if trade_allowed:
        suggested_size_pct = round(min(0.25, meta_score * 0.3), 4)

    return {
        "symbol": symbol,
        "meta_score": round(meta_score, 4),
        "historical_accuracy": round(historical_accuracy, 4),
        "trade_allowed": trade_allowed,
        "suggested_size_pct": suggested_size_pct,
        "samples_used": len(sym_logs),
    }


def filter_target_weights(
    target_weights: Dict[str, float],
    signals: Dict[str, Dict[str, Any]],
    resolved_logs: List[Dict[str, Any]],
    cutoff_ts: Optional[float] = None,
) -> Dict[str, float]:
    """Zero out weights where meta filter rejects the trade."""
    filtered: Dict[str, float] = {}
    for sym, weight in target_weights.items():
        sig = signals.get(sym) or {}
        meta = compute_meta_score(
            symbol=sym,
            prediction=int(sig.get("prediction", 0)),
            confidence=float(sig.get("confidence") or 0),
            resolved_logs=resolved_logs,
            cutoff_ts=cutoff_ts,
        )
        if meta["trade_allowed"]:
            filtered[sym] = weight
    return filtered
