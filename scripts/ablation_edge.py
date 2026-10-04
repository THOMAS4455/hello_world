#!/usr/bin/env python3
"""Ablation harness: does each part of the model beat the majority-class baseline?

Every variant is scored on exactly the same purged expanding-window folds
(ImprovedPredictor.walk_forward_folds), and the metric of record is
EDGE = accuracy - majority_class_baseline rather than raw accuracy, because the
fixed-horizon label is heavily imbalanced.

Variants
    constant            always predict the training fold's majority class
    momentum_rule       trend_strength > 0 (the simple rule the screener leads with)
    single_gb           one GradientBoosting classifier, no ensemble
    ensemble            the shipped three-layer path
    ensemble_no_regime  shipped path with the regime layer weight forced to 0

Requires real bars in data/market.sqlite. It never fabricates data: if the
store is empty this exits non-zero instead of substituting a random walk.

Usage:
    python scripts/ablation_edge.py --symbol 600519
    python scripts/ablation_edge.py --symbol 600519 --folds 4 --horizon 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

EVAL_DIR = PROJECT_ROOT / "data" / "live_eval"
MIN_BARS = 400


def _wilson(successes: int, n: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    import math

    if n <= 0:
        return 0.0, 0.0
    phat = successes / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2 * n)
    spread = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom)


def _score(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
    from sklearn.metrics import balanced_accuracy_score, matthews_corrcoef

    n = len(y_true)
    if n == 0:
        return {"n": 0}
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / n
    positives = sum(y_true) / n
    baseline = max(positives, 1.0 - positives)
    low, high = _wilson(correct, n)
    return {
        "n": n,
        "accuracy": accuracy,
        "baseline_accuracy": baseline,
        "edge": accuracy - baseline,
        "edge_ci95": [low - baseline, high - baseline],
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "bullish_rate": sum(y_pred) / n,
    }


def load_frame(symbol: str):
    from validation.market_store import MarketStore

    store = MarketStore()
    df = store.load_bars(symbol)
    if df.empty:
        raise SystemExit(
            "no local bars for %s in %s -- run scripts/daily_live_validation.py first "
            "(this harness never substitutes synthetic data)" % (symbol, store.path)
        )
    if len(df) < MIN_BARS:
        raise SystemExit(
            "only %d bars for %s; need at least %d for purged walk-forward"
            % (len(df), symbol, MIN_BARS)
        )
    return df


def build_dataset(df, horizon: int, up_threshold: float):
    """Return aligned (X, y, features) using the shipped feature engineering."""
    from src.core.improved_predictor import ImprovedPredictor, align_features_and_labels

    prep = ImprovedPredictor()
    features = prep.prepare_features(df)
    labels = prep.prepare_labels(features, horizon=horizon, up_threshold=up_threshold)
    features, labels = align_features_and_labels(features, labels)
    prep.adopt_prepared_features()
    columns = list(prep.feature_columns)
    return features[columns], labels, features, columns


def run(args: argparse.Namespace) -> int:
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier

    from src.core.improved_predictor import ImprovedPredictor

    df = load_frame(args.symbol)
    X, y, features, columns = build_dataset(df, args.horizon, args.up_threshold)
    total_n = len(X)

    folds = list(
        ImprovedPredictor.walk_forward_folds(total_n, args.folds, args.test_size, args.horizon)
    )
    usable = [f for f in folds if f[1] >= 80 and (f[3] - f[2]) >= 30]
    if not usable:
        raise SystemExit(
            "no usable folds: %d rows, folds=%s (need >=80 train rows and >=30 test rows)"
            % (total_n, folds)
        )

    variants = [
        "constant",
        "momentum_rule",
        "single_gb",
        "ensemble",
        "ensemble_no_regime",
    ]
    predictions: Dict[str, List[List[int]]] = {v: [] for v in variants}
    truths: List[List[int]] = []

    for train_start, train_end, test_start, test_end in usable:
        X_train, y_train = X.iloc[train_start:train_end], y.iloc[train_start:train_end]
        X_test, y_test = X.iloc[test_start:test_end], y.iloc[test_start:test_end]
        f_train = features.iloc[train_start:train_end]
        f_test = features.iloc[test_start:test_end]

        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue

        y_test_list = [int(v) for v in y_test.tolist()]
        truths.append(y_test_list)

        # (c) majority-class constant
        majority = int(round(float(y_train.mean())))
        predictions["constant"].append([majority] * len(y_test_list))

        # (d) simple trend rule
        trend = f_test["trend_strength"].fillna(0.0).to_numpy()
        predictions["momentum_rule"].append([1 if v > 0 else 0 for v in trend])

        # (b) a single model, same features
        gb = GradientBoostingClassifier(
            n_estimators=120, learning_rate=0.05, max_depth=5,
            min_samples_split=10, min_samples_leaf=5, subsample=0.75, random_state=42,
        )
        gb.fit(X_train, y_train)
        predictions["single_gb"].append([int(v) for v in gb.predict(X_test)])

        # (a) shipped ensemble
        predictor = ImprovedPredictor(learn_weights=False)
        predictor.feature_columns = list(columns)
        predictor.inference_columns = list(columns)
        predictor._train_vol_threshold = float(f_train["volatility_30"].quantile(0.75))
        bundle = predictor._fit_ensemble_bundle(X_train, y_train, f_train)
        threshold, calibrator, _ = predictor._fit_validation_artifacts(
            X_train, y_train, f_train
        )
        raw = predictor._predict_ensemble_up(bundle, X_test, f_test)
        calibrated = predictor._calibrate_probs(calibrator, raw)
        predictions["ensemble"].append([int(v) for v in (calibrated > threshold).astype(int)])

        # (e) ablation: drop the regime layer
        saved = dict(predictor.layer_weights)
        traditional = saved["baseline"] + saved["enhanced"]
        if traditional > 0:
            predictor.layer_weights = {
                "baseline": saved["baseline"] / traditional,
                "enhanced": saved["enhanced"] / traditional,
                "regime": 0.0,
            }
        raw_no_regime = predictor._predict_ensemble_up(bundle, X_test, f_test)
        calibrated_no_regime = predictor._calibrate_probs(calibrator, raw_no_regime)
        predictions["ensemble_no_regime"].append(
            [int(v) for v in (calibrated_no_regime > threshold).astype(int)]
        )
        predictor.layer_weights = saved

    if not truths:
        raise SystemExit("every fold was rejected (single-class labels)")

    flat_true = [t for fold in truths for t in fold]
    results: Dict[str, Any] = {}
    for variant in variants:
        flat_pred = [p for fold in predictions[variant] for p in fold]
        if len(flat_pred) != len(flat_true):
            raise SystemExit(
                "variant %s produced %d predictions for %d labels"
                % (variant, len(flat_pred), len(flat_true))
            )
        results[variant] = _score(flat_true, flat_pred)

    # Multiplicity correction for the search over variants.
    try:
        from validation.overfit_guard import deflated_sharpe_ratio

        edge_series = np.array(
            [results[v]["edge"] for v in variants if results[v].get("n")], dtype=float
        )
        results["_multiplicity"] = {
            "n_variants_tested": len(edge_series),
            "note": "deflated_sharpe_ratio is applied to return streams elsewhere; "
                    "edge itself is reported with a Wilson interval per variant",
            "dsr_available": callable(deflated_sharpe_ratio),
        }
    except Exception:
        pass

    payload = {
        "generated_at": time.time(),
        "symbol": args.symbol,
        "bars": int(len(df)),
        "rows_after_features": int(total_n),
        "horizon": args.horizon,
        "up_threshold": args.up_threshold,
        "folds_used": len(truths),
        "n_out_of_sample": len(flat_true),
        "label_positive_rate": float(sum(flat_true) / len(flat_true)),
        "variants": results,
        "evidence_grade": "[全量实测]" if len(flat_true) >= 200 else "[抽样估计]",
    }

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVAL_DIR / ("ablation_%s_%s.json" % (args.symbol, time.strftime("%Y%m%d")))
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    header = "%-20s %6s %8s %8s %9s %8s" % ("variant", "n", "acc", "baseline", "edge", "mcc")
    print(header)
    print("-" * len(header))
    for variant in variants:
        r = results[variant]
        print("%-20s %6d %8.4f %8.4f %+9.4f %8.4f"
              % (variant, r["n"], r["accuracy"], r["baseline_accuracy"], r["edge"], r["mcc"]))
    print("")
    print("out-of-sample rows: %d (folds=%d)  grade=%s" % (len(flat_true), len(truths), payload["evidence_grade"]))
    print("written: %s" % out_path)
    return 0


def run_all(args: argparse.Namespace) -> int:
    """Run the ablation for every symbol that has enough stored bars."""
    from validation.market_store import MarketStore

    store = MarketStore()
    symbols = [s for s in store.symbols() if store.bar_count(s) >= MIN_BARS]
    if not symbols:
        raise SystemExit(
            "no symbol has >= %d stored bars in %s; run scripts/daily_live_validation.py first"
            % (MIN_BARS, store.path)
        )
    print("symbols with enough bars: %s" % ", ".join(symbols))
    exit_code = 0
    for symbol in symbols:
        print("")
        print("=== %s ===" % symbol)
        sub = argparse.Namespace(**vars(args))
        sub.symbol = symbol
        sub.all_symbols = False
        exit_code = max(exit_code, run(sub))
    return exit_code


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="purged walk-forward edge ablation")
    parser.add_argument("--symbol", help="symbol to evaluate")
    parser.add_argument("--all-symbols", action="store_true",
                        help="evaluate every stored symbol with enough bars")
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--test-size", type=float, default=0.12)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--up-threshold", type=float, default=0.02)
    return parser.parse_args(argv)


if __name__ == "__main__":
    _args = parse_args()
    if not _args.symbol and not _args.all_symbols:
        raise SystemExit("pass --symbol SYMBOL or --all-symbols")
    sys.exit(run_all(_args) if _args.all_symbols else run(_args))
