import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.task_state import STATUS_FAILED, STATUS_SUCCEEDED
from backend.app.db.repositories.result_repo import get_result_by_task_id
from backend.app.db.repositories.task_repo import get_task
from backend.app.db.session import get_db

router = APIRouter()


@router.get("/report/{task_id}")
async def get_report(task_id: str, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task 不存在")

    if task.status == STATUS_FAILED:
        return {
            "task_id": task.id,
            "status": task.status,
            "error_code": task.error_code,
            "error_message": task.error_message,
            "result": None,
        }

    if task.status != STATUS_SUCCEEDED:
        raise HTTPException(
            status_code=409,
            detail={
                "task_id": task.id,
                "status": task.status,
                "error_code": task.error_code,
                "error_message": task.error_message,
            },
        )

    model = get_result_by_task_id(db, task_id)
    if not model:
        raise HTTPException(status_code=404, detail="task 结果不存在")
    return {
        "task_id": task.id,
        "status": task.status,
        "result": json.loads(model.result_json),
    }
