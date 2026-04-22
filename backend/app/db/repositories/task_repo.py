from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.core.realtime.task_stream import publish_task_update
from backend.app.core.task_state import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
)
from backend.app.db.models import AnalysisTask
from backend.app.db.repositories.task_event_repo import create_task_event


def create_task(
    db: Session,
    *,
    file_name: str,
    file_size: int,
    file_path: str,
    content_type: Optional[str],
) -> AnalysisTask:
    task = AnalysisTask(
        status=STATUS_QUEUED,
        current_stage="upload",
        progress=5,
        file_name=file_name,
        file_size=file_size,
        file_path=file_path,
        content_type=content_type,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    create_task_event(
        db,
        task_id=task.id,
        stage="upload",
        event_type="created",
        message="文件上传完成，任务已入队",
        progress=task.progress,
    )
    publish_task_update(task)
    return task


def get_task(db: Session, task_id: str) -> Optional[AnalysisTask]:
    return db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()


def list_tasks(db: Session, limit: int = 20, offset: int = 0) -> list[AnalysisTask]:
    return (
        db.query(AnalysisTask)
        .order_by(AnalysisTask.created_at.desc())
        .offset(max(0, offset))
        .limit(min(max(limit, 1), 100))
        .all()
    )


def set_task_running(db: Session, task: AnalysisTask) -> AnalysisTask:
    task.status = STATUS_RUNNING
    task.current_stage = "ocr"
    task.progress = 15
    task.error_code = None
    task.error_message = None
    task.started_at = datetime.now(timezone.utc)
    task.finished_at = None
    db.commit()
    db.refresh(task)
    create_task_event(
        db,
        task_id=task.id,
        stage=task.current_stage,
        event_type="status",
        message="任务开始执行",
        progress=task.progress,
    )
    publish_task_update(task)
    return task


def update_task_stage(db: Session, task: AnalysisTask, *, stage: str, progress: int) -> AnalysisTask:
    task.current_stage = stage
    task.progress = max(0, min(progress, 100))
    db.commit()
    db.refresh(task)
    create_task_event(
        db,
        task_id=task.id,
        stage=task.current_stage,
        event_type="stage",
        message=f"进入 {task.current_stage} 阶段",
        progress=task.progress,
    )
    publish_task_update(task)
    return task


def set_task_succeeded(db: Session, task: AnalysisTask) -> AnalysisTask:
    task.status = STATUS_SUCCEEDED
    task.current_stage = "done"
    task.progress = 100
    task.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    create_task_event(
        db,
        task_id=task.id,
        stage="done",
        event_type="status",
        message="任务执行成功",
        progress=task.progress,
    )
    publish_task_update(task)
    return task


def set_task_failed(db: Session, task: AnalysisTask, *, error_code: str, error_message: str) -> AnalysisTask:
    task.status = STATUS_FAILED
    task.current_stage = "done"
    task.progress = 100
    task.error_code = error_code
    task.error_message = error_message[:4000]
    task.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    create_task_event(
        db,
        task_id=task.id,
        stage="done",
        event_type="error",
        message=f"[{task.error_code}] {task.error_message}",
        progress=task.progress,
    )
    publish_task_update(task)
    return task


def set_task_cancelled(
    db: Session,
    task: AnalysisTask,
    *,
    reason: str = "任务已取消",
) -> AnalysisTask:
    task.status = STATUS_CANCELLED
    task.current_stage = "done"
    task.progress = 100
    task.error_code = "TASK_CANCELLED"
    task.error_message = reason[:4000]
    task.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    create_task_event(
        db,
        task_id=task.id,
        stage="done",
        event_type="status",
        message=task.error_message or "任务已取消",
        progress=task.progress,
    )
    publish_task_update(task)
    return task
