"""Tests for portfolio metrics."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from portfolio.portfolio_metrics import compare_strategies, compute_metrics


def test_compute_metrics_positive_trend():
    curve = [1.0, 1.01, 1.02, 1.03, 1.05]
    metrics = compute_metrics(curve)
    assert metrics["total_return"] > 0
    assert metrics["days"] == 4


def test_compare_strategies():
    strat = [1.0, 1.05, 1.08, 1.10]
    bench = [1.0, 1.02, 1.03, 1.04]
    result = compare_strategies(strat, bench)
    assert "strategy" in result
    assert "benchmark" in result
    assert result["excess_return"] > 0
