"""Idempotency and label_mode persistence for SignalTracker.record."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from validation.signal_tracker import SignalTracker  # noqa: E402


def _tracker(tmp_path: Path) -> SignalTracker:
    return SignalTracker(storage_path=tmp_path / "signal_logs.json")


def test_same_symbol_same_day_is_recorded_once(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path)

    first = tracker.record("000001", 1, "up", 0.7, 5, 0.02, ensemble_up=0.65)
    second = tracker.record("000001", 1, "up", 0.7, 5, 0.02, ensemble_up=0.65)

    assert first == second, "repeat recording must return the existing id"
    payload = json.loads((tmp_path / "signal_logs.json").read_text(encoding="utf-8"))
    assert len(payload["logs"]) == 1


def test_different_symbols_and_horizons_are_distinct(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path)

    tracker.record("000001", 1, "up", 0.7, 5, 0.02)
    tracker.record("600519", 1, "up", 0.7, 5, 0.02)
    tracker.record("000001", 1, "up", 0.7, 10, 0.02)

    payload = json.loads((tmp_path / "signal_logs.json").read_text(encoding="utf-8"))
    assert len(payload["logs"]) == 3


def test_label_mode_is_persisted(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path)
    tracker.record("000001", 1, "up", 0.7, 5, 0.02, label_mode="triple_barrier")

    payload = json.loads((tmp_path / "signal_logs.json").read_text(encoding="utf-8"))
    assert payload["logs"][0]["label_mode"] == "triple_barrier"


def test_resolved_entry_can_be_recorded_again(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path)
    log_id = tracker.record("000001", 1, "up", 0.7, 5, 0.02)

    payload = json.loads((tmp_path / "signal_logs.json").read_text(encoding="utf-8"))
    payload["logs"][0]["outcome_resolved"] = True
    (tmp_path / "signal_logs.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    new_id = tracker.record("000001", 1, "up", 0.7, 5, 0.02)
    assert new_id != log_id, "a settled signal must not block a new day's signal"
