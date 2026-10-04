"""
Task management endpoints — poll progress and cancel long-running operations.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.common import error_response, success_response
from flask_services.task_manager import task_manager

router = APIRouter(tags=["tasks"])


@router.get("/api/tasks/status")
async def task_status(task_id: str = Query(..., min_length=1)):
    task = task_manager.get_status(task_id)
    if task is None:
        return error_response("Task not found", {})
    return success_response(task)


@router.post("/api/tasks/cancel")
async def task_cancel(task_id: str = Query(..., min_length=1)):
    ok = task_manager.cancel(task_id)
    if not ok:
        return error_response("Task not found or already completed")
    return success_response({"task_id": task_id, "cancelled": True}, "Task cancelled")


@router.get("/api/tasks/list")
async def task_list(limit: int = Query(default=20, ge=1, le=100)):
    tasks = task_manager.list_tasks(limit)
    return success_response({"tasks": tasks, "count": len(tasks)})
