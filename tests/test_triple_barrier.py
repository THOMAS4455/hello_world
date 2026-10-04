"""Tests for triple-barrier labeling."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from validation.triple_barrier import label_triple_barrier


def test_upper_barrier_hit():
    result = label_triple_barrier(
        entry_price=100.0,
        closes=[100.5, 101.0, 103.0],
        up_threshold=0.02,
        stop_loss_pct=0.02,
    )
    assert result["barrier"] == "upper"
    assert result["return"] > 0.02


def test_lower_barrier_hit():
    result = label_triple_barrier(
        entry_price=100.0,
        closes=[99.5, 98.0, 97.0],
        up_threshold=0.02,
        stop_loss_pct=0.02,
    )
    assert result["barrier"] == "lower"
    assert result["return"] < 0


def test_time_barrier():
    result = label_triple_barrier(
        entry_price=100.0,
        closes=[100.1, 100.2, 100.0],
        up_threshold=0.05,
        stop_loss_pct=0.05,
    )
    assert result["barrier"] == "time"
