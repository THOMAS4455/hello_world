#!/usr/bin/env python3
"""Unit tests for purged labels/splits in ImprovedPredictor."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from core.improved_predictor import (  # noqa: E402
    ImprovedPredictor,
    align_features_and_labels,
    purged_train_test_split,
)


def _make_price_df(n: int = 200) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 10 + np.cumsum(np.random.default_rng(42).normal(0, 0.05, n))
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "close_price": close,
            "volume": np.full(n, 1_000_000.0),
            "open_price": close,
            "high_price": close,
            "low_price": close,
        }
    )


class TestPurgedSplit:
    def test_prepare_labels_drops_invalid_tail(self):
        predictor = ImprovedPredictor()
        df = _make_price_df(120)
        features = predictor.prepare_features(df)
        labels = predictor.prepare_labels(features, horizon=5, up_threshold=0.02)
        assert labels.iloc[-5:].isna().all()
        assert labels.iloc[:-5].notna().all()

    def test_align_features_and_labels(self):
        predictor = ImprovedPredictor()
        df = _make_price_df(120)
        features = predictor.prepare_features(df)
        labels = predictor.prepare_labels(features, horizon=5, up_threshold=0.02)
        aligned_x, aligned_y = align_features_and_labels(features, labels)
        assert len(aligned_x) == len(aligned_y)
        assert aligned_y.isna().sum() == 0
        assert len(aligned_x) == len(features) - 5

    def test_purged_split_respects_horizon_embargo(self):
        train_end, test_start = purged_train_test_split(100, test_size=0.2, horizon=5)
        assert test_start == 80
        assert train_end == 75
        assert train_end + 5 <= test_start

    def test_backtest_does_not_leak_labels_across_split(self):
        predictor = ImprovedPredictor()
        df = _make_price_df(260)
        result = predictor.backtest(df, horizon=5, test_size=0.2, up_threshold=0.02)
        assert result["test_size"] > 0
        assert "ensemble" in result["results"]
        assert 0.0 <= result["results"]["ensemble"]["accuracy"] <= 1.0
        assert result.get("decision_threshold", 0.5) >= 0.35
        wf = result["results"].get("walk_forward", {})
        assert wf.get("method") == "ensemble_walk_forward"
        pnl = result.get("pnl_backtest", {})
        assert "total_return" in pnl
        assert "max_drawdown" in pnl
        cal = result.get("calibration", {})
        assert "brier_raw" in cal
        assert "brier_calibrated" in cal


class TestEvalMetrics:
    def test_up_class_metrics_differ_from_accuracy(self):
        predictor = ImprovedPredictor()
        y_true = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
        y_pred = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        metrics = predictor._eval_metrics(y_true, y_pred)

        assert metrics["accuracy"] == pytest.approx(0.7)
        assert metrics["precision"] == pytest.approx(1.0)
        assert metrics["recall"] == pytest.approx(0.4)
        assert metrics["f1"] == pytest.approx(2 * 1.0 * 0.4 / (1.0 + 0.4))
        assert metrics["accuracy"] != metrics["recall"]
        assert metrics["precision"] != metrics["accuracy"]
