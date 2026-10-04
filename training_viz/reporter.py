"""
TrainingProgressReporter — bridges the ML training loop to the task manager.
Receives callback events from ImprovedPredictor.train() and writes structured
training_details to the task manager so the frontend can poll and visualize.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List


class TrainingProgressReporter:
    """Receives training events and writes structured progress to the task manager."""

    def __init__(self, task_manager, task_id: str) -> None:
        self._tm = task_manager
        self._task_id = task_id
        self._lock = threading.Lock()
        self._models: Dict[str, Dict[str, Any]] = {}
        self._models_trained = 0
        self._total_models = 0
        self._current_layer = ""
        self._current_model = ""
        self._lstm = {"status": "pending", "message": ""}
        self._regime = {"status": "pending", "regimes_trained": [], "total_regimes": 4}
        self._weights = {"status": "pending"}
        self._base_progress = 30

    # ── public API used by prediction_service ──

    def init_models(self, model_ids: List[str]) -> None:
        with self._lock:
            self._total_models = len(model_ids)
            for mid in model_ids:
                self._models[mid] = {
                    "status": "pending",
                    "cv_mean": None,
                    "cv_std": None,
                    "error": None,
                    "layer": mid.split(":")[0] if ":" in mid else "",
                }
            self._flush()

    def on_callback(self, event: Dict[str, Any]) -> None:
        """Unified callback — receives events from ImprovedPredictor.train()."""
        etype = event.get("event", "")
        if etype == "phase":
            self._on_phase(event.get("phase", ""))
        elif etype == "model_training":
            self._on_model_training(event["model_id"], event.get("layer", ""))
        elif etype == "model_done":
            self._on_model_done(
                event["model_id"],
                float(event.get("cv_mean", 0)),
                float(event.get("cv_std", 0)),
            )
        elif etype == "model_error":
            self._on_model_error(event["model_id"], event.get("error", ""))
        elif etype == "regime_start":
            self._on_regime_start()
        elif etype == "regime_progress":
            self._on_regime_progress(event.get("regime", ""), event.get("status", ""))
        elif etype == "regime_done":
            self._on_regime_done()
        elif etype == "lstm_start":
            self._on_lstm_start()
        elif etype == "lstm_done":
            self._on_lstm_done()
        elif etype == "lstm_skipped":
            self._on_lstm_skipped(event.get("reason", ""))
        elif etype == "lstm_error":
            self._on_lstm_error(event.get("error", ""))
        elif etype == "weights_start":
            self._on_weights_start()
        elif etype == "weights_done":
            self._on_weights_done()
        elif etype == "weights_skipped":
            self._on_weights_skipped()
        elif etype == "training_complete":
            self._on_training_complete()

    # ── internal event handlers ──

    def _on_phase(self, phase: str) -> None:
        pct = {"prepare_features": 15, "prepare_labels": 22, "calibration": 26, "split_data": 28}.get(phase, 30)
        self._tm.update_progress(self._task_id, pct, "preparing", f"{phase}...")

    def _on_model_training(self, model_id: str, layer: str) -> None:
        with self._lock:
            self._current_layer = layer
            self._current_model = model_id
            if model_id in self._models:
                self._models[model_id]["status"] = "training"
            else:
                self._models[model_id] = {
                    "status": "training",
                    "cv_mean": None,
                    "cv_std": None,
                    "error": None,
                    "layer": layer,
                }
            self._flush()

    def _on_model_done(self, model_id: str, cv_mean: float, cv_std: float) -> None:
        with self._lock:
            if model_id in self._models:
                self._models[model_id]["status"] = "done"
                self._models[model_id]["cv_mean"] = round(cv_mean, 4)
                self._models[model_id]["cv_std"] = round(cv_std, 4)
            self._models_trained += 1
            self._flush()

    def _on_model_error(self, model_id: str, error: str) -> None:
        with self._lock:
            if model_id in self._models:
                self._models[model_id]["status"] = "error"
                self._models[model_id]["error"] = error
            self._models_trained += 1
            self._flush()

    def _on_regime_start(self) -> None:
        with self._lock:
            self._regime["status"] = "training"
            self._current_layer = "regime"
            self._flush()

    def _on_regime_progress(self, regime: str, status: str) -> None:
        with self._lock:
            if status == "done" and regime not in self._regime["regimes_trained"]:
                self._regime["regimes_trained"].append(regime)
            self._flush()

    def _on_regime_done(self) -> None:
        with self._lock:
            self._regime["status"] = "done"
            self._flush()

    def _on_lstm_start(self) -> None:
        with self._lock:
            self._lstm["status"] = "training"
            self._lstm["message"] = "Training LSTM..."
            self._current_layer = "lstm"
            self._flush()

    def _on_lstm_done(self) -> None:
        with self._lock:
            self._lstm["status"] = "done"
            self._lstm["message"] = "LSTM complete"
            self._flush()

    def _on_lstm_skipped(self, reason: str = "") -> None:
        with self._lock:
            self._lstm["status"] = "skipped"
            self._lstm["message"] = reason or "LSTM not available"
            self._flush()

    def _on_lstm_error(self, error: str) -> None:
        with self._lock:
            self._lstm["status"] = "error"
            self._lstm["message"] = error
            self._flush()

    def _on_weights_start(self) -> None:
        with self._lock:
            self._weights["status"] = "training"
            self._current_layer = "weights"
            self._flush()

    def _on_weights_done(self) -> None:
        with self._lock:
            self._weights["status"] = "done"
            self._flush()

    def _on_weights_skipped(self) -> None:
        with self._lock:
            self._weights["status"] = "skipped"
            self._flush()

    def _on_training_complete(self) -> None:
        with self._lock:
            self._current_layer = "done"
            self._current_model = ""
            self._flush()

    # ── internal helpers ──

    def _compute_progress(self) -> int:
        if self._total_models == 0:
            return self._base_progress
        fraction = min(1.0, self._models_trained / max(1, self._total_models))
        return self._base_progress + int(fraction * 35)

    def _build_details(self) -> Dict[str, Any]:
        return {
            "models": dict(self._models),
            "current_layer": self._current_layer,
            "current_model": self._current_model,
            "models_trained": self._models_trained,
            "total_models": self._total_models,
            "lstm": dict(self._lstm),
            "regime": dict(self._regime),
            "weight_optimization": dict(self._weights),
        }

    def _flush(self) -> None:
        details = self._build_details()
        progress = self._compute_progress()
        stage_msg = (
            f"Training {self._current_model} ({self._models_trained}/{self._total_models})"
            if self._current_model
            else f"Training models ({self._models_trained}/{self._total_models})..."
        )
        self._tm.update_progress(self._task_id, progress, "training_models", stage_msg)
        self._tm.update_training(self._task_id, details)


def create_reporter(task_manager, task_id: str) -> TrainingProgressReporter:
    return TrainingProgressReporter(task_manager, task_id)
