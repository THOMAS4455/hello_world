"""
In-memory task manager for long-running async operations (predictions, backtests, data fetches).

Tasks are stored in a dict with progress, stage, and cancellation support.
Clients poll /api/tasks/status?task_id=xxx for updates.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional


class TaskManager:
    """Thread-safe registry of background tasks with progress tracking."""

    _MAX_TASKS = 200
    _CLEANUP_AFTER_SECONDS = 30 * 60  # 30 minutes

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def _now(self) -> float:
        return time.time()

    def create(self, task_type: str, description: str = "") -> str:
        """Register a new task and return its ID. The caller is responsible for
        calling update_progress / complete / fail."""
        task_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "description": description,
                "status": "pending",
                "progress": 0,
                "stage": "",
                "stage_message": "",
                "result": None,
                "error": None,
                "created_at": self._now(),
                "completed_at": None,
                "cancelled": False,
            }
            # Prevent unbounded growth
            if len(self._tasks) > self._MAX_TASKS:
                oldest = sorted(
                    self._tasks.values(),
                    key=lambda t: t["completed_at"] or t["created_at"],
                )[: len(self._tasks) - self._MAX_TASKS]
                for t in oldest:
                    if t["status"] in ("done", "error", "cancelled"):
                        self._tasks.pop(t["id"], None)
        return task_id

    def update_progress(
        self,
        task_id: str,
        progress: int,
        stage: str = "",
        stage_message: str = "",
    ) -> None:
        """progress: 0-100 integer. stage: short label. stage_message: human-readable."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task["status"] = "running"
                task["progress"] = max(0, min(100, int(progress)))
                task["stage"] = stage or task.get("stage", "")
                task["stage_message"] = stage_message or task.get("stage_message", "")

    def complete(self, task_id: str, result: Any = None) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task["status"] = "done"
                task["progress"] = 100
                task["result"] = result
                task["completed_at"] = self._now()

    def fail(self, task_id: str, error: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task["status"] = "error"
                task["error"] = error
                task["completed_at"] = self._now()

    def cancel(self, task_id: str) -> bool:
        """Request cancellation. The running code must check is_cancelled()."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task["status"] in ("pending", "running"):
                task["cancelled"] = True
                task["status"] = "cancelled"
                task["completed_at"] = self._now()
                return True
            return False

    def is_cancelled(self, task_id: str) -> bool:
        """Called by running tasks to check if they should abort."""
        with self._lock:
            task = self._tasks.get(task_id)
            return bool(task and task["cancelled"])

    def update_training(self, task_id: str, training_details: dict) -> None:
        """Store per-model training progress on the task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task["training_details"] = training_details

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return dict(task)  # shallow copy

    def list_tasks(self, limit: int = 20) -> list:
        with self._lock:
            items = sorted(
                self._tasks.values(),
                key=lambda t: t["created_at"],
                reverse=True,
            )
            return [dict(t) for t in items[:limit]]

    def cleanup(self) -> int:
        """Remove old completed tasks. Returns count removed."""
        now = self._now()
        removed = 0
        with self._lock:
            stale = [
                tid
                for tid, t in self._tasks.items()
                if t["status"] in ("done", "error", "cancelled")
                and (now - (t.get("completed_at") or t.get("created_at"))) > self._CLEANUP_AFTER_SECONDS
            ]
            for tid in stale:
                del self._tasks[tid]
                removed += 1
        return removed


task_manager = TaskManager()
