"""Tests for point-in-time prediction (no look-ahead in replay mode)."""

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from flask_services.prediction_service import PredictionService


def _make_df(n: int = 120) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "close_price": [10.0 + i * 0.1 for i in range(n)],
            "open_price": [10.0 + i * 0.1 for i in range(n)],
            "high_price": [10.0 + i * 0.1 for i in range(n)],
            "low_price": [10.0 + i * 0.1 for i in range(n)],
            "volume": [1_000_000] * n,
            "turnover_rate": [0.01] * n,
        }
    )


def test_truncate_df_as_of():
    df = _make_df()
    trimmed = PredictionService._truncate_df_as_of(df, "2024-06-01")
    assert len(trimmed) < len(df)
    assert len(trimmed) >= 80
    assert pd.to_datetime(trimmed["date"]).max() <= pd.Timestamp("2024-06-01")


def test_predict_stock_replay_skips_signal_log():
    svc = PredictionService()
    df = _make_df()
    mock_pred = {
        "prediction": 1,
        "confidence": 0.7,
        "individual_predictions": {},
        "probabilities": {},
        "layer_outputs": {},
        "decision_threshold": 0.5,
        "calibration_applied": False,
    }
    with patch.object(svc, "_load_history_df", return_value=df.copy()):
        with patch.object(svc, "_ensure_model_ready", return_value=PredictionService._truncate_df_as_of(df, "2024-06-01")):
            with patch.object(svc.predictor, "predict", return_value=mock_pred):
                with patch.object(svc.predictor, "get_prediction_explanation", return_value="ok"):
                    with patch.object(svc, "_record_signal_log") as mock_log:
                        result = svc.predict_stock(
                            "000001",
                            as_of_date="2024-06-01",
                            record_signal=False,
                        )
                        assert result["replay_mode"] is True
                        mock_log.assert_not_called()
