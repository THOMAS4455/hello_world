import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from research.factor_backtest import run_momentum_backtest


def _make_histories(n_syms=40, n_days=300, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n_days)
    hist = {}
    for i in range(n_syms):
        drift = rng.uniform(-0.006, 0.006)
        close = 20 * np.exp(np.cumsum(drift + rng.standard_normal(n_days) * 0.01))
        hist[f"s{i:03d}"] = pd.DataFrame({"date": dates, "close_price": close})
    return hist


def test_momentum_detects_persistent_drift():
    report = run_momentum_backtest(_make_histories(), horizon=5, rebalance_every=5, lookback=(20, 60))
    assert "error" not in report
    assert report["ic_mean"] > 0.3
    assert report["ic_positive_frac"] > 0.8
    assert report["top_mean_return_per_period"] > report["bottom_mean_return_per_period"]


def test_insufficient_history_returns_error():
    hist = {
        f"s{i}": pd.DataFrame(
            {"date": pd.bdate_range("2024-01-01", periods=30), "close_price": [1.0] * 30}
        )
        for i in range(5)
    }
    report = run_momentum_backtest(hist, min_history=80)
    assert "error" in report
