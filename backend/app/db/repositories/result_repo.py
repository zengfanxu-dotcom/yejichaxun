import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.db.models import AnalysisResult


def _extract_summary(result: dict[str, Any]) -> tuple[str, float, int, int]:
    review_status = str(result.get("评审状态") or "失败")
    summary = result.get("得分摘要") or {}
    if not isinstance(summary, dict):
        summary = {}
    total_score = float(summary.get("最终总得分") or 0.0)
    valid_count = int(summary.get("有效业绩总数") or 0)
    invalid_count = int(summary.get("无效业绩总数") or 0)
    return review_status, total_score, valid_count, invalid_count


def upsert_result(
    db: Session,
    *,
    task_id: str,
    result: dict[str, Any],
    rag_context: Optional[str] = None,
) -> AnalysisResult:
    review_status, total_score, valid_count, invalid_count = _extract_summary(result)
    model = db.query(AnalysisResult).filter(AnalysisResult.task_id == task_id).first()
    payload = json.dumps(result, ensure_ascii=False)
    if model is None:
        model = AnalysisResult(
            task_id=task_id,
            review_status=review_status,
            total_score=total_score,
            valid_count=valid_count,
            invalid_count=invalid_count,
            result_json=payload,
            rag_context=rag_context,
        )
        db.add(model)
    else:
        model.review_status = review_status
        model.total_score = total_score
        model.valid_count = valid_count
        model.invalid_count = invalid_count
        model.result_json = payload
        model.rag_context = rag_context
    db.commit()
    db.refresh(model)
    return model


def get_result_by_task_id(db: Session, task_id: str) -> Optional[AnalysisResult]:
    return db.query(AnalysisResult).filter(AnalysisResult.task_id == task_id).first()
