import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.agent.analyzer import analyze_tender
from backend.app.core.realtime.task_stream import publish_task_update
from backend.app.core.task_state import (
    STATUS_CANCELLED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
)
from backend.app.core.tools.ocr_tool import ocr_tool
from backend.app.core.tools.rag_runtime import query_topk_context
from backend.app.db.repositories.result_repo import upsert_result
from backend.app.db.repositories.task_event_repo import create_task_event
from backend.app.db.repositories.task_repo import (
    get_task,
    set_task_failed,
    set_task_running,
    set_task_succeeded,
    update_task_stage,
)
from backend.app.db.session import SessionLocal, get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_task_file(path: str) -> bytes:
    if not os.path.exists(path):
        raise FileNotFoundError(f"任务文件不存在: {path}")
    with open(path, "rb") as f:
        return f.read()


def _error_code_by_stage(stage: str) -> str:
    mapping = {
        "ocr": "OCR_FAILED",
        "rag": "RAG_FAILED",
        "llm": "LLM_FAILED",
    }
    return mapping.get(stage, "ANALYSIS_FAILED")


def _is_cancelled(db: Session, task_id: str) -> bool:
    task = get_task(db, task_id)
    return bool(task and task.status == STATUS_CANCELLED)


def _run_analysis_pipeline(task_id: str) -> None:
    db = SessionLocal()
    active_stage = "ocr"
    try:
        task = get_task(db, task_id)
        if not task:
            logger.error("后台任务不存在: %s", task_id)
            return
        if task.status == STATUS_CANCELLED:
            return

        content = _load_task_file(task.file_path)
        file_name = task.file_name
        file_size = len(content)

        update_task_stage(db, task, stage="ocr", progress=25)
        text = ocr_tool.extract_text(content, file_name, file_size)
        if not text or not text.strip():
            raise ValueError("未提取到文本内容")
        if _is_cancelled(db, task_id):
            return

        active_stage = "rag"
        update_task_stage(db, task, stage="rag", progress=55)
        rag_context = query_topk_context(tender_text=text)
        if _is_cancelled(db, task_id):
            return

        active_stage = "llm"
        update_task_stage(db, task, stage="llm", progress=85)
        result = analyze_tender(text=text, rag_context=rag_context)
        if _is_cancelled(db, task_id):
            return

        update_task_stage(db, task, stage="postprocess", progress=95)
        upsert_result(db, task_id=task.id, result=result, rag_context=rag_context)
        if _is_cancelled(db, task_id):
            return
        set_task_succeeded(db, task)
    except Exception as e:
        task = get_task(db, task_id)
        if task and task.status == STATUS_CANCELLED:
            logger.info("后台任务已取消，停止后续写入: %s", task_id)
            return
        error_code = _error_code_by_stage(active_stage)
        if task:
            set_task_failed(db, task, error_code=error_code, error_message=str(e))
        logger.error("后台任务分析失败 task_id=%s: %s", task_id, e, exc_info=True)
    finally:
        db.close()


@router.post("/analyze/{task_id}")
async def analyze_task(task_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task 不存在")

    if task.status == STATUS_RUNNING:
        raise HTTPException(status_code=409, detail="task 正在运行")
    if task.status == STATUS_SUCCEEDED:
        return {
            "task_id": task.id,
            "status": task.status,
            "current_stage": task.current_stage,
            "progress": task.progress,
            "message": "task 已完成",
        }
    if task.status == STATUS_CANCELLED:
        task.status = STATUS_QUEUED
        task.error_code = None
        task.error_message = None
        task.current_stage = "upload"
        task.progress = 5
        task.started_at = None
        task.finished_at = None
        db.commit()
        db.refresh(task)
        create_task_event(
            db,
            task_id=task.id,
            stage="upload",
            event_type="retry",
            message="任务已重置，准备重新分析",
            progress=task.progress,
        )
        publish_task_update(task)

    set_task_running(db, task)
    background_tasks.add_task(_run_analysis_pipeline, task.id)
    return {
        "task_id": task.id,
        "status": task.status,
        "current_stage": task.current_stage,
        "progress": task.progress,
        "message": "task 已进入后台分析",
    }
