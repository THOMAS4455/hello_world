"""Tests for meta-labeling filter."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from validation.meta_label_filter import compute_meta_score, filter_target_weights


def test_low_accuracy_filters_trade():
    logs = [
        {
            "symbol": "000001",
            "outcome_resolved": True,
            "outcome_correct": False,
            "recorded_at": i,
        }
        for i in range(10)
    ]
    meta = compute_meta_score(
        symbol="000001",
        prediction=1,
        confidence=0.6,
        resolved_logs=logs,
    )
    assert meta["trade_allowed"] is False


def test_filter_target_weights():
    signals = {"000001": {"prediction": 1, "confidence": 0.8}}
    logs = [
        {"symbol": "000001", "outcome_resolved": True, "outcome_correct": True, "recorded_at": 1}
        for _ in range(8)
    ]
    filtered = filter_target_weights({"000001": 0.5}, signals, logs)
    assert "000001" in filtered
