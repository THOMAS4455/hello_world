"""Meta-labeling cutoff by simulation date."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from validation.meta_label_filter import compute_meta_score


def test_meta_respects_cutoff_ts():
    logs = [
        {"symbol": "000001", "outcome_resolved": True, "outcome_correct": True, "recorded_at": 100.0},
        {"symbol": "000001", "outcome_resolved": True, "outcome_correct": False, "recorded_at": 200.0},
    ]
    early = compute_meta_score(
        symbol="000001",
        prediction=1,
        confidence=0.8,
        resolved_logs=logs,
        cutoff_ts=150.0,
        min_samples=1,
    )
    assert early["samples_used"] == 1
    assert early["historical_accuracy"] == 1.0
