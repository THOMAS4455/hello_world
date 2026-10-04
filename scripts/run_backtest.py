#!/usr/bin/env python3
"""
MVP Backtest — Core Algorithm Profitability Verification

Single-file script. Fetches real A-share data, runs the full 3-layer ensemble
pipeline (features → training → backtest with constraints), and outputs a
clear profitability report.

Usage:  python scripts/run_backtest.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
import pandas as pd

# Ensure project root and src are importable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Clear proxy env vars (required for akshare in mainland China networks)
import os as _os
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    _os.environ[_k] = ""
import urllib3 as _urllib3
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Stock pool — representative A-share stocks across sectors
# ---------------------------------------------------------------------------
STOCK_POOL = [
    ("000001", "平安银行", "银行"),
    ("600519", "贵州茅台", "白酒"),
    ("000858", "五粮液",   "白酒"),
    ("300750", "宁德时代", "新能源"),
    ("601318", "中国平安", "保险"),
]

HORIZON = 5
UP_THRESHOLD = 0.02
TEST_SIZE = 0.25
LABEL_METHODS = ("fixed_horizon", "triple_barrier")
LOOKBACK_DAYS = 2000


# ===========================================================================
# Data Fetching
# ===========================================================================

def _to_tencent_symbol(code: str) -> str:
    """Convert numeric code to Tencent symbol format: sh600519 or sz000001."""
    code = code.strip()
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def fetch_stock_history(code: str) -> Optional[pd.DataFrame]:
    """Fetch historical daily data via Tencent K-line API (no akshare dependency)."""
    import json as _json

    symbol = _to_tencent_symbol(code)
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {"param": f"{symbol},day,,,{LOOKBACK_DAYS},"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    session = requests.Session()
    session.trust_env = False
    session.proxies = {"http": None, "https": None}

    try:
        resp = session.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        data = _json.loads(resp.text)
        stock_data = data.get("data", {}).get(symbol, {})
        rows = stock_data.get("day") or stock_data.get("qfqday") or []
        if not rows or len(rows) < 200:
            return None

        # Tencent K-line format: date, open, close, high, low, volume, amount
        cols = ["date", "open_price", "close_price", "high_price", "low_price", "volume"]
        df = pd.DataFrame([r[:6] for r in rows], columns=cols)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["open_price", "close_price", "high_price", "low_price", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["close_price", "volume"])
        return df.sort_values("date").reset_index(drop=True) if len(df) >= 200 else None
    except Exception:
        return None


# ===========================================================================
# Core Pipeline
# ===========================================================================

def run_pipeline(
    df: pd.DataFrame,
    code: str,
    name: str,
    label_method: str,
    use_constraints: bool,
) -> Dict[str, Any]:
    """Run the full prediction + backtest pipeline for one stock."""
    from src.core.improved_predictor import ImprovedPredictor
    from src.trading.constraints import TradingConstraints

    t_start = time.time()

    predictor = ImprovedPredictor(learn_weights=False)
    _features = predictor.prepare_features(df)
    n_features = len(predictor.feature_columns)

    # Train
    t0 = time.time()
    predictor.train(
        df, horizon=HORIZON, up_threshold=UP_THRESHOLD,
        fast=True, label_method=label_method,
    )
    t_train = time.time() - t0

    # Backtest
    t0 = time.time()
    constraints = TradingConstraints() if use_constraints else None
    result = predictor.backtest(
        df, horizon=HORIZON, test_size=TEST_SIZE,
        label_method=label_method,
    )
    t_backtest = time.time() - t0

    ensemble = result["results"]["ensemble"]
    baseline = result["baseline_accuracy"]
    pnl = result.get("pnl_backtest", {})
    wf = result.get("walk_forward", {}) or result.get("results", {}).get("walk_forward", {})

    return {
        "code": code,
        "name": name,
        "label_method": label_method,
        "use_constraints": use_constraints,
        "n_features": n_features,
        "n_rows": len(df),
        "t_train": t_train,
        "t_backtest": t_backtest,
        "t_total": time.time() - t_start,
        "accuracy": float(ensemble["accuracy"]),
        "precision": float(ensemble.get("precision", 0)),
        "recall": float(ensemble.get("recall", 0)),
        "f1": float(ensemble.get("f1", 0)),
        "baseline_accuracy": float(baseline),
        "improvement": float(result.get("improvement", 0)),
        "wf_accuracy": float(wf.get("accuracy", 0)),
        "wf_samples": int(wf.get("samples", 0)),
        "total_return": float(pnl.get("total_return", 0)),
        "buy_hold_return": float(pnl.get("buy_hold_return", 0)),
        "excess_return": float(pnl.get("excess_return", 0)),
        "sharpe_ratio": float(pnl.get("sharpe_ratio", 0)),
        "max_drawdown": float(pnl.get("max_drawdown", 0)),
        "buy_hold_max_drawdown": float(pnl.get("buy_hold_max_drawdown", 0)),
        "win_rate": float(pnl.get("win_rate", 0)),
        "active_days": int(pnl.get("active_days", 0)),
        "trade_signals": int(pnl.get("trade_signals", 0)),
        "decision_threshold": float(pnl.get("decision_threshold", result.get("decision_threshold", 0.5))),
        "note": str(pnl.get("note", "")),
        "model_scores": predictor.model_scores,
        "feature_importance_top10": sorted(
            predictor.feature_importance_scores.items(), key=lambda x: -x[1]
        )[:10] if predictor.feature_importance_scores else [],
    }


# ===========================================================================
# Report Formatting
# ===========================================================================

def print_header(text: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")

def print_stock_result(r: Dict[str, Any]) -> None:
    tag = "有约束" if r["use_constraints"] else "无约束"
    print(f"\n  [{r['code']} {r['name']}] {r['label_method']:>15s} | {tag}")
    print(f"  {'─'*62}")
    print(f"  样本: {r['n_rows']}天  |  特征: {r['n_features']}  |  "
          f"训练: {r['t_train']:.0f}s  |  回测: {r['t_backtest']:.0f}s")
    print(f"  准确率: {r['accuracy']:.1%}  |  基线: {r['baseline_accuracy']:.1%}  |  "
          f"提升: {r['improvement']:+.1%}  |  WF: {r['wf_accuracy']:.1%}")
    print(f"  总收益: {r['total_return']:.2%}  |  买入持有: {r['buy_hold_return']:.2%}  |  "
          f"超额: {r['excess_return']:.2%}")
    print(f"  Sharpe: {r['sharpe_ratio']:.2f}  |  最大回撤: {r['max_drawdown']:.2%}  |  "
          f"胜率: {r['win_rate']:.1%}  |  信号: {r['trade_signals']}")


def print_summary(results: List[Dict[str, Any]]) -> None:
    print_header("PER-STOCK SUMMARY")

    # Group by method
    for method in LABEL_METHODS:
        subset = [r for r in results if r["label_method"] == method and r["use_constraints"]]
        if not subset:
            continue
        print(f"\n── {method} (with constraints) ──")
        print(f"  {'代码':<8} {'名称':<10} {'准确率':>7} {'提升':>7} {'总收益':>8} "
              f"{'Sharpe':>7} {'最大回撤':>8} {'胜率':>6} {'信号':>5}")
        for r in subset:
            print(f"  {r['code']:<8} {r['name']:<10} {r['accuracy']:>6.1%} {r['improvement']:>+6.1%} "
                  f"{r['total_return']:>7.2%} {r['sharpe_ratio']:>6.2f} {r['max_drawdown']:>7.2%} "
                  f"{r['win_rate']:>5.1%} {r['trade_signals']:>4d}")

        # Average
        avg_acc = np.mean([r["accuracy"] for r in subset])
        avg_imp = np.mean([r["improvement"] for r in subset])
        avg_ret = np.mean([r["total_return"] for r in subset])
        avg_sharpe = np.mean([r["sharpe_ratio"] for r in subset])
        print(f"  {'─'*55}")
        print(f"  {'平均':<18} {avg_acc:>6.1%} {avg_imp:>+6.1%} {avg_ret:>7.2%} "
              f"{avg_sharpe:>6.2f}")


def print_method_comparison(results: List[Dict[str, Any]]) -> None:
    print_header("METHOD COMPARISON (fixed_horizon vs triple_barrier)")

    for use_constraints in [True, False]:
        tag = "WITH constraints" if use_constraints else "NO constraints"
        print(f"\n── {tag} ──")
        for method in LABEL_METHODS:
            subset = [r for r in results if r["label_method"] == method and r["use_constraints"] == use_constraints]
            if not subset:
                continue
            n = len(subset)
            avg_acc = np.mean([r["accuracy"] for r in subset])
            avg_imp = np.mean([r["improvement"] for r in subset])
            avg_ret = np.mean([r["total_return"] for r in subset])
            avg_sharpe = np.mean([r["sharpe_ratio"] for r in subset])
            avg_wf = np.mean([r["wf_accuracy"] for r in subset])
            print(f"  {method:>15s} | stocks={n} | acc={avg_acc:.1%} | imp={avg_imp:+.1%} | "
                  f"ret={avg_ret:.2%} | sharpe={avg_sharpe:.2f} | wf={avg_wf:.1%}")


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    print_header("ALPHASCOPE MVP BACKTEST")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Horizon: {HORIZON}d  |  Threshold: {UP_THRESHOLD:.0%}  |  Test: {TEST_SIZE:.0%}")

    # ── 1. Fetch data ──
    print_header("FETCHING DATA")
    stock_data: Dict[str, pd.DataFrame] = {}
    for code, name, sector in STOCK_POOL:
        status = "..."
        df = fetch_stock_history(code)
        if df is not None and len(df) >= 200:
            stock_data[code] = df
            status = f"OK ({len(df)} days, {df['close_price'].iloc[-1]:.2f})"
        else:
            status = "FAILED"
        print(f"  {code} {name:<6} {status}")

    if not stock_data:
        print("\n  No stock data fetched. Check network/akshare.")
        return

    # ── 2. Run pipeline ──
    print_header("RUNNING PIPELINE")
    all_results: List[Dict[str, Any]] = []

    for code, df in stock_data.items():
        name = next((n for c, n, _ in STOCK_POOL if c == code), code)
        for label_method in LABEL_METHODS:
            for use_constraints in [True, False]:
                try:
                    r = run_pipeline(df, code, name, label_method, use_constraints)
                    all_results.append(r)
                    print_stock_result(r)
                except Exception as exc:
                    print(f"\n  [{code}] {label_method} ERROR: {exc}")

    if not all_results:
        print("\n  All pipeline runs failed.")
        return

    # ── 3. Summary ──
    print_summary(all_results)
    print_method_comparison(all_results)

    # ── 4. Feature importance (aggregated) ──
    print_header("AGGREGATED FEATURE IMPORTANCE")
    all_imps: Dict[str, List[float]] = {}
    for r in all_results:
        for feat, imp in r.get("feature_importance_top10", []):
            all_imps.setdefault(feat, []).append(float(imp))
    avg_imps = sorted(
        [(feat, np.mean(vals)) for feat, vals in all_imps.items()], key=lambda x: -x[1]
    )[:15]
    for feat, imp in avg_imps:
        bar = "█" * int(imp / max(1, avg_imps[0][1]) * 30)
        print(f"  {feat:35s} {imp:8.2f}  {bar}")

    # ── 5. Best / Worst ──
    print_header("BEST / WORST")
    constrained = [r for r in all_results if r["use_constraints"]]
    if constrained:
        best = max(constrained, key=lambda r: r["sharpe_ratio"])
        worst = min(constrained, key=lambda r: r["sharpe_ratio"])
        print(f"  Best:  [{best['code']} {best['name']}] {best['label_method']} "
              f"Sharpe={best['sharpe_ratio']:.2f} Ret={best['total_return']:.2%}")
        print(f"  Worst: [{worst['code']} {worst['name']}] {worst['label_method']} "
              f"Sharpe={worst['sharpe_ratio']:.2f} Ret={worst['total_return']:.2%}")

    print_header("DONE")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
