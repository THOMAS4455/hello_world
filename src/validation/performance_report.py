"""Live performance report for recorded prediction signals.

This module answers one question with full-population statistics: does the
model beat the trivial majority-class baseline on realized outcomes?

Conventions that matter:

* Accuracy alone is meaningless for the fixed-horizon label (1 = "5-day return
  above +2%"), because 60-90% of days are 0. The headline metric is therefore
  EDGE = accuracy - majority_class_baseline, reported together with n and a
  Wilson interval.
* Below MIN_SAMPLES the report is explicitly marked insufficient_n and no
  improvement may be claimed.
* Both a recomputed accuracy and the accuracy implied by the stored
  outcome_correct flags are reported, so the two sources can be reconciled.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

DEFAULT_SIGNAL_LOG = Path(__file__).resolve().parents[2] / "data" / "signal_logs.json"
DEFAULT_EVAL_DIR = Path(__file__).resolve().parents[2] / "data" / "live_eval"
MIN_SAMPLES = 200
_Z95 = 1.959963984540054


# --------------------------------------------------------------------- helpers
def wilson_interval(successes: int, n: int, z: float = _Z95) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return 0.0, 0.0
    phat = successes / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2 * n)
    spread = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom)


def matthews_corrcoef(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """MCC without a sklearn import (defined as 0 for degenerate inputs)."""
    tp = fp = tn = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == 1 and p == 1:
            tp += 1
        elif t == 0 and p == 1:
            fp += 1
        elif t == 0 and p == 0:
            tn += 1
        else:
            fn += 1
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denom == 0:
        return 0.0
    return (tp * tn - fp * fn) / denom


def balanced_accuracy(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """Mean of per-class recall; NaN-free fallback when a class is absent."""
    recalls: List[float] = []
    for cls in (0, 1):
        idx = [i for i, t in enumerate(y_true) if t == cls]
        if not idx:
            continue
        recalls.append(sum(1 for i in idx if y_pred[i] == cls) / len(idx))
    if not recalls:
        return 0.0
    return float(sum(recalls) / len(recalls))


def spearman_ic(probs: Sequence[float], returns: Sequence[float]) -> Dict[str, Any]:
    """Spearman rank IC between predicted probability and realized return."""
    paired = [(float(p), float(r)) for p, r in zip(probs, returns) if p is not None]
    n = len(paired)
    if n < 3:
        return {"ic": None, "t_stat": None, "n": n}
    frame = pd.DataFrame(paired, columns=["prob", "ret"])
    ic = float(frame["prob"].corr(frame["ret"], method="spearman"))
    if not np.isfinite(ic):
        return {"ic": None, "t_stat": None, "n": n}
    t_stat: Optional[float] = None
    if abs(ic) < 1.0 and n > 2:
        t_stat = float(ic * math.sqrt((n - 2) / max(1e-12, 1.0 - ic * ic)))
    return {"ic": ic, "t_stat": t_stat, "n": n}


def load_resolved_logs(signal_log_path: Path = DEFAULT_SIGNAL_LOG) -> Dict[str, Any]:
    """Return the raw log payload plus every outcome-resolved entry."""
    path = Path(signal_log_path)
    if not path.exists():
        return {"path": str(path), "total": 0, "pending": 0, "resolved": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # surfaced, never swallowed
        raise ValueError("cannot parse %s: %s" % (path, exc))
    logs = payload.get("logs") or []
    resolved = [x for x in logs if x.get("outcome_resolved")]
    return {
        "path": str(path),
        "total": len(logs),
        "pending": len(logs) - len(resolved),
        "resolved": resolved,
    }


# ---------------------------------------------------------------------- report
def build_report(
    logs: List[Dict[str, Any]],
    *,
    min_samples: int = MIN_SAMPLES,
) -> Dict[str, Any]:
    """Full-population statistics over every resolved signal in logs."""
    resolved = [x for x in logs if x.get("outcome_resolved") and x.get("outcome_return") is not None]
    n = len(resolved)
    if n == 0:
        return {
            "generated_at": time.time(),
            "n_resolved": 0,
            "n_pending": None,
            "insufficient_n": True,
            "min_samples": min_samples,
            "evidence_grade": "[未验证]",
            "message": "no resolved signals yet: performance is unverified",
        }

    y_pred: List[int] = []
    y_true: List[int] = []
    stored_flags: List[int] = []
    probs: List[Optional[float]] = []
    returns: List[float] = []

    for entry in resolved:
        pred = int(entry.get("prediction", 0))
        ret = float(entry["outcome_return"])
        threshold = float(entry.get("up_threshold", 0.02))
        y_pred.append(pred)
        y_true.append(1 if ret > threshold else 0)
        stored_flags.append(1 if entry.get("outcome_correct") else 0)
        probs.append(entry.get("ensemble_up"))
        returns.append(ret)

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / n
    positives = sum(y_true)
    baseline = max(positives / n, 1.0 - positives / n)
    edge = accuracy - baseline
    lo, hi = wilson_interval(correct, n)
    stored_correct = sum(stored_flags)
    stored_accuracy = stored_correct / n

    prob_entries = [p for p in probs if p is not None]
    brier = None
    if len(prob_entries) == n:
        brier = float(np.mean([(float(p) - t) ** 2 for p, t in zip(prob_entries, y_true)]))

    ic = spearman_ic(prob_entries, returns)

    report: Dict[str, Any] = {
        "generated_at": time.time(),
        "n_resolved": n,
        "n_pending": None,
        "min_samples": min_samples,
        "insufficient_n": n < min_samples,
        "positive_rate": positives / n,
        "accuracy": accuracy,
        "baseline_accuracy": baseline,
        "edge": edge,
        "edge_ci95": [lo - baseline, hi - baseline],
        "accuracy_ci95": [lo, hi],
        "balanced_accuracy": balanced_accuracy(y_true, y_pred),
        "mcc": matthews_corrcoef(y_true, y_pred),
        "brier": brier,
        "ic": ic["ic"],
        "ic_t_stat": ic["t_stat"],
        "ic_n": ic["n"],
        "accuracy_from_stored_flags": stored_accuracy,
        "reconciliation_mismatch": abs(stored_accuracy - accuracy) > 1e-9,
        "bullish_signals": sum(y_pred),
    }

    if n < min_samples:
        report["evidence_grade"] = "[未验证]"
        report["message"] = (
            "n=%d < min_samples=%d: insufficient sample, no improvement can be claimed"
            % (n, min_samples)
        )
    else:
        report["evidence_grade"] = "[全量实测]"
        report["message"] = (
            "edge=%+.4f vs majority-class baseline (n=%d, Wilson 95%% CI %+.4f..%+.4f)"
            % (edge, n, lo - baseline, hi - baseline)
        )
    return report


# ---------------------------------------------------------------- persistence
def upsert_ledger_line(ledger_path: Path, date_key: str, record: Dict[str, Any]) -> bool:
    """One line per date; rewrite the file only when replacing that date.

    Returns True when a new line was appended.
    """
    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    if ledger_path.exists():
        lines = [ln for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    entry = json.dumps({"date": date_key, **record}, ensure_ascii=False, sort_keys=True)
    appended = True
    replaced = False
    for i, line in enumerate(lines):
        try:
            existing = json.loads(line)
        except Exception:
            continue
        if existing.get("date") == date_key:
            lines[i] = entry
            replaced = True
            appended = False
            break
    if not replaced:
        lines.append(entry)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return appended


def write_report(
    report: Dict[str, Any],
    *,
    eval_dir: Path = DEFAULT_EVAL_DIR,
    date_key: Optional[str] = None,
    counters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persist report to latest.json and to the monthly append-only ledger."""
    eval_dir = Path(eval_dir)
    eval_dir.mkdir(parents=True, exist_ok=True)
    date_key = date_key or time.strftime("%Y-%m-%d")
    month_key = date_key[:7]

    if counters:
        report = {**report, **counters}

    latest_path = eval_dir / "latest.json"
    latest_path.write_text(
        json.dumps({"date": date_key, **report}, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    ledger_fields = {
        "n_resolved": report.get("n_resolved"),
        "n_pending": report.get("n_pending"),
        "accuracy": report.get("accuracy"),
        "baseline_accuracy": report.get("baseline_accuracy"),
        "edge": report.get("edge"),
        "edge_ci95": report.get("edge_ci95"),
        "balanced_accuracy": report.get("balanced_accuracy"),
        "mcc": report.get("mcc"),
        "brier": report.get("brier"),
        "ic": report.get("ic"),
        "ic_t_stat": report.get("ic_t_stat"),
        "insufficient_n": report.get("insufficient_n"),
        "status": report.get("status"),
    }
    ledger_path = eval_dir / ("ledger_%s.jsonl" % month_key.replace("-", ""))
    appended = upsert_ledger_line(ledger_path, date_key, ledger_fields)
    return {"latest": str(latest_path), "ledger": str(ledger_path), "ledger_appended": appended}


def summarize_for_log(report: Dict[str, Any]) -> str:
    """One-line summary; never claims improvement when the sample is too small."""
    if report.get("n_resolved", 0) == 0:
        return "live performance: no resolved signals (unverified)"
    head = report.get("message", "")
    grade = report.get("evidence_grade", "[未验证]")
    return "%s live performance: %s" % (grade, head)
