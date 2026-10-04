"""Triple-Barrier labeling (TBM-lite) for path-aware signal outcomes."""

from __future__ import annotations

from typing import Any, Dict, List


def label_triple_barrier(
    *,
    entry_price: float,
    closes: List[float],
    up_threshold: float = 0.02,
    stop_loss_pct: float = 0.02,
) -> Dict[str, Any]:
    """Return label and realized return based on first barrier touched."""
    if entry_price <= 0 or not closes:
        return {"label": 0, "return": 0.0, "barrier": "time", "days_held": 0}

    upper = entry_price * (1.0 + up_threshold)
    lower = entry_price * (1.0 - stop_loss_pct)

    for i, close in enumerate(closes):
        price = float(close)
        if price >= upper:
            ret = price / entry_price - 1.0
            return {"label": 1, "return": ret, "barrier": "upper", "days_held": i + 1}
        if price <= lower:
            ret = price / entry_price - 1.0
            return {"label": -1, "return": ret, "barrier": "lower", "days_held": i + 1}

    final = float(closes[-1])
    ret = final / entry_price - 1.0
    return {"label": 0, "return": ret, "barrier": "time", "days_held": len(closes)}


def barrier_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate barrier touch counts from resolved log rows."""
    counts = {"upper": 0, "lower": 0, "time": 0}
    for row in rows:
        barrier = str(row.get("barrier_hit") or row.get("barrier") or "time")
        if barrier in counts:
            counts[barrier] += 1
    total = sum(counts.values()) or 1
    return {
        "counts": counts,
        "upper_pct": counts["upper"] / total,
        "lower_pct": counts["lower"] / total,
        "time_pct": counts["time"] / total,
    }
