from collections import defaultdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.task_state import (
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    is_cancellable,
)
from backend.app.db.repositories.task_event_repo import (
    list_task_events,
    list_task_events_chronological,
    list_task_events_for_task_ids,
)
from backend.app.db.repositories.task_repo import get_task, list_tasks, set_task_cancelled
from backend.app.db.session import get_db

router = APIRouter()
PIPELINE_STAGES = ("ocr", "rag", "llm", "postprocess")


def _task_to_dict(task) -> dict:
    return {
        "task_id": task.id,
        "status": task.status,
        "current_stage": task.current_stage,
        "progress": task.progress,
        "file_name": task.file_name,
        "file_size": task.file_size,
        "error_code": task.error_code,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


def _event_to_dict(event) -> dict:
    return {
        "event_id": event.id,
        "task_id": event.task_id,
        "stage": event.stage,
        "event_type": event.event_type,
        "message": event.message,
        "progress": event.progress,
        "created_at": event.created_at,
    }


def _duration_ms(start: datetime | None, end: datetime | None) -> int:
    if not start or not end:
        return 0
    return max(int((end - start).total_seconds() * 1000), 0)


def _calculate_stage_durations(events: list, finished_at: datetime | None) -> tuple[dict[str, int], int]:
    if not events:
        return {}, 0
    starts: dict[str, datetime] = {}
    durations = defaultdict(int)
    first_at = events[0].created_at
    last_at = finished_at or events[-1].created_at

    for event in events:
        if event.stage in PIPELINE_STAGES and event.event_type in ("status", "stage"):
            starts[event.stage] = event.created_at
        if event.stage == "done":
            for stage, stage_start in list(starts.items()):
                durations[stage] += _duration_ms(stage_start, event.created_at)
                starts.pop(stage, None)

    for stage, stage_start in starts.items():
        durations[stage] += _duration_ms(stage_start, last_at)
    total_duration_ms = _duration_ms(first_at, last_at)
    return dict(durations), total_duration_ms


@router.get("/tasks/metrics")
async def get_task_metrics(
    limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    tasks = list_tasks(db, limit=limit, offset=0)
    total = len(tasks)
    status_counts = defaultdict(int)
    failure_code_counts = defaultdict(int)
    for task in tasks:
        status_counts[task.status] += 1
        if task.status == STATUS_FAILED:
            failure_code_counts[task.error_code or "UNKNOWN_FAILED"] += 1

    task_ids = [task.id for task in tasks]
    retry_events = list_task_events_for_task_ids(db, task_ids=task_ids, event_type="retry")
    retried_task_ids = {item.task_id for item in retry_events}
    retried_task_count = len(retried_task_ids)
    retried_success_count = sum(1 for task in tasks if task.id in retried_task_ids and task.status == STATUS_SUCCEEDED)
    retried_success_rate = (retried_success_count / retried_task_count) if retried_task_count else 0.0

    avg_stage_duration_ms: dict[str, int] = {}
    stage_totals = defaultdict(int)
    stage_task_counts = defaultdict(int)
    events = list_task_events_for_task_ids(db, task_ids=task_ids)
    grouped_events: dict[str, list] = defaultdict(list)
    for item in events:
        grouped_events[item.task_id].append(item)
    task_map = {task.id: task for task in tasks}
    for task_id, task_events in grouped_events.items():
        stage_durations_ms, _ = _calculate_stage_durations(task_events, task_map.get(task_id).finished_at if task_map.get(task_id) else None)
        for stage, value in stage_durations_ms.items():
            stage_totals[stage] += value
            stage_task_counts[stage] += 1
    for stage in PIPELINE_STAGES:
        if stage_task_counts[stage]:
            avg_stage_duration_ms[stage] = int(stage_totals[stage] / stage_task_counts[stage])

    succeeded = status_counts[STATUS_SUCCEEDED]
    failed = status_counts[STATUS_FAILED]
    return {
        "window_size": total,
        "status_counts": dict(status_counts),
        "success_rate": (succeeded / total) if total else 0.0,
        "failure_rate": (failed / total) if total else 0.0,
        "failure_code_counts": dict(failure_code_counts),
        "retry": {
            "retried_task_count": retried_task_count,
            "retried_success_count": retried_success_count,
            "retried_success_rate": retried_success_rate,
        },
        "avg_stage_duration_ms": avg_stage_duration_ms,
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: UUID, db: Session = Depends(get_db)):
    task = get_task(db, str(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="task 不存在")
    return _task_to_dict(task)


@router.get("/tasks")
async def get_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    tasks = list_tasks(db, limit=limit, offset=offset)
    return {"items": [_task_to_dict(t) for t in tasks], "limit": limit, "offset": offset}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: UUID, db: Session = Depends(get_db)):
    task = get_task(db, str(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="task 不存在")

    if not is_cancellable(task.status):
        raise HTTPException(status_code=409, detail=f"task 当前状态为 {task.status}，不可取消")

    set_task_cancelled(db, task, reason="用户取消任务")
    return _task_to_dict(task)


@router.get("/tasks/{task_id}/events")
async def get_task_events(
    task_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    task_id_str = str(task_id)
    task = get_task(db, task_id_str)
    if not task:
        raise HTTPException(status_code=404, detail="task 不存在")
    events = list_task_events(db, task_id=task_id_str, limit=limit, offset=offset)
    chronological_events = list_task_events_chronological(db, task_id=task_id_str)
    stage_durations_ms, total_duration_ms = _calculate_stage_durations(chronological_events, task.finished_at)
    return {
        "items": [_event_to_dict(item) for item in events],
        "limit": limit,
        "offset": offset,
        "stage_durations_ms": stage_durations_ms,
        "total_duration_ms": total_duration_ms,
    }


