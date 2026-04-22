import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.db.repositories.task_repo import create_task
from backend.app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _upload_dir() -> str:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../uploads"))
    os.makedirs(path, exist_ok=True)
    return path


@router.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        file_name = file.filename or "unknown"
        file_size = len(content)
        if file_size == 0:
            raise HTTPException(status_code=400, detail="空文件无法分析")

        task_safe_name = f"{uuid.uuid4()}_{file_name}"
        file_path = os.path.join(_upload_dir(), task_safe_name)
        with open(file_path, "wb") as f:
            f.write(content)

        task = create_task(
            db,
            file_name=file_name,
            file_size=file_size,
            file_path=file_path,
            content_type=file.content_type,
        )
        return {
            "task_id": task.id,
            "status": task.status,
            "current_stage": task.current_stage,
            "progress": task.progress,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("上传失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")