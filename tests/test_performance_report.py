"""Tests for the live performance report.

The decisive property: a model that only ever predicts the majority class must
score edge == 0. If that ever fails, the edge metric is lying.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from validation.performance_report import (  # noqa: E402
    build_report,
    matthews_corrcoef,
    upsert_ledger_line,
    wilson_interval,
)

THRESHOLD = 0.02


def _entry(prediction: int, outcome_return: float, ensemble_up=0.5, threshold=THRESHOLD):
    return {
        "symbol": "000001",
        "prediction": prediction,
        "outcome_return": outcome_return,
        "outcome_resolved": True,
        "up_threshold": threshold,
        "ensemble_up": ensemble_up,
    }


def test_majority_class_predictor_has_zero_edge() -> None:
    # 6 of 8 outcomes are labelled 0, so the majority-class baseline is 0.75.
    returns = [0.10, 0.06, 0.0, -0.01, -0.02, 0.0, 0.01, -0.03]
    logs = [_entry(0, r) for r in returns]

    report = build_report(logs, min_samples=1)

    assert report["baseline_accuracy"] == pytest.approx(0.75)
    assert report["accuracy"] == pytest.approx(0.75)
    assert report["edge"] == pytest.approx(0.0)
    assert report["mcc"] == pytest.approx(0.0)


def test_perfect_predictor_edges_above_baseline() -> None:
    logs = [
        _entry(1, 0.05),
        _entry(1, 0.03),
        _entry(0, 0.0),
        _entry(0, -0.02),
    ]
    report = build_report(logs, min_samples=1)

    assert report["accuracy"] == pytest.approx(1.0)
    assert report["baseline_accuracy"] == pytest.approx(0.5)
    assert report["edge"] == pytest.approx(0.5)
    assert report["mcc"] == pytest.approx(1.0)


def test_small_sample_is_flagged_unverified() -> None:
    logs = [_entry(1, 0.05), _entry(0, 0.0)]
    report = build_report(logs, min_samples=200)

    assert report["insufficient_n"] is True
    assert report["evidence_grade"] == "[未验证]"
    assert "insufficient" in report["message"]
    # The wording must explicitly refuse a claim, not merely avoid the word.
    assert "no improvement can be claimed" in report["message"]
    assert "edge=" not in report["message"]


def test_edge_ci_spans_zero_for_tiny_samples() -> None:
    # 2 of 8 outcomes are up, so the majority-class baseline is 0.75.
    # Always predicting 0 scores exactly the baseline (6/8 correct) and the
    # Wilson interval for edge must straddle zero at this sample size.
    returns = [0.05, 0.03, 0.0, -0.01, 0.0, 0.01, 0.0, -0.03]
    predictions = [0, 0, 0, 0, 0, 0, 0, 0]
    logs = [_entry(p, r) for p, r in zip(predictions, returns)]

    report = build_report(logs, min_samples=1)

    assert report["edge"] == pytest.approx(0.0)
    low, high = report["edge_ci95"]
    assert low < 0 < high


def test_empty_input_reports_unverified() -> None:
    report = build_report([], min_samples=200)

    assert report["n_resolved"] == 0
    assert report["insufficient_n"] is True
    assert report["evidence_grade"] == "[未验证]"


def test_reconciliation_mismatch_is_detected() -> None:
    good = [_entry(1, 0.05)]
    good[0]["outcome_correct"] = True
    assert build_report(good, min_samples=1)["reconciliation_mismatch"] is False

    bad = [_entry(1, 0.05)]
    bad[0]["outcome_correct"] = False
    assert build_report(bad, min_samples=1)["reconciliation_mismatch"] is True


def test_ic_sign_follows_probability_ordering() -> None:
    logs = [
        _entry(1, 0.05, ensemble_up=0.9),
        _entry(1, 0.03, ensemble_up=0.8),
        _entry(0, -0.01, ensemble_up=0.2),
        _entry(0, -0.02, ensemble_up=0.1),
    ]
    report = build_report(logs, min_samples=1)
    assert report["ic"] is not None and report["ic"] > 0


def test_wilson_interval_is_bounded() -> None:
    low, high = wilson_interval(0, 0)
    assert (low, high) == (0.0, 0.0)

    low, high = wilson_interval(7, 10)
    assert 0.0 <= low < 0.7 < high <= 1.0


def test_mcc_degenerate_input_is_zero() -> None:
    assert matthews_corrcoef([1, 1], [1, 1]) == 0.0


def test_ledger_is_one_line_per_date(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger_202610.jsonl"

    assert upsert_ledger_line(ledger, "2026-10-04", {"edge": 0.1}) is True
    assert upsert_ledger_line(ledger, "2026-10-04", {"edge": 0.2}) is False
    assert upsert_ledger_line(ledger, "2026-10-05", {"edge": 0.3}) is True

    lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    assert '"edge": 0.2' in lines[0], "same-date rerun must replace, not duplicate"
