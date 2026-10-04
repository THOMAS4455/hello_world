"""Tests for signal tracking."""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from validation.signal_tracker import SignalTracker


def test_signal_tracker_record_and_stats(tmp_path):
    tracker = SignalTracker(tmp_path / "signal_logs.json")
    tracker.record("000001", 1, "up", 0.72, 5, 0.02, ensemble_up=0.68)
    # Recording the same symbol/horizon again on the same calendar day is a
    # deliberate no-op: the live sample unit is one signal per symbol per day,
    # otherwise repeated (cache-served) predictions inflate the sample.
    tracker.record("000001", 0, "down", 0.45, 5, 0.02, ensemble_up=0.42)

    tracker.resolve_outcomes(
        {
            "000001": {"outcome_return": 0.03},
        }
    )
    stats = tracker.get_stats("000001", limit=10)
    assert stats["samples"] == 1
    assert stats["resolved_samples"] == 1
    assert stats["accuracy"] >= 0.0


def test_signal_tracker_keeps_distinct_horizons(tmp_path):
    tracker = SignalTracker(tmp_path / "signal_logs.json")
    tracker.record("000001", 1, "up", 0.72, 5, 0.02)
    tracker.record("000001", 1, "up", 0.72, 10, 0.02)

    payload = json.loads((tmp_path / "signal_logs.json").read_text(encoding="utf-8"))
    assert len(payload["logs"]) == 2
