from collections.abc import Sequence

from sqlalchemy import asc
from sqlalchemy.orm import Session

from backend.app.db.models import AnalysisTaskEvent


def create_task_event(
    db: Session,
    *,
    task_id: str,
    stage: str,
    event_type: str,
    message: str,
    progress: int | None = None,
) -> AnalysisTaskEvent:
    model = AnalysisTaskEvent(
        task_id=task_id,
        stage=stage[:32],
        event_type=event_type[:32],
        message=message[:4000],
        progress=progress,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def list_task_events(db: Session, *, task_id: str, limit: int = 100, offset: int = 0) -> list[AnalysisTaskEvent]:
    return (
        db.query(AnalysisTaskEvent)
        .filter(AnalysisTaskEvent.task_id == task_id)
        .order_by(AnalysisTaskEvent.created_at.desc())
        .offset(max(0, offset))
        .limit(min(max(limit, 1), 200))
        .all()
    )


def list_task_events_chronological(db: Session, *, task_id: str) -> list[AnalysisTaskEvent]:
    return (
        db.query(AnalysisTaskEvent)
        .filter(AnalysisTaskEvent.task_id == task_id)
        .order_by(asc(AnalysisTaskEvent.created_at))
        .all()
    )


def list_task_events_for_task_ids(
    db: Session,
    *,
    task_ids: Sequence[str],
    event_type: str | None = None,
) -> list[AnalysisTaskEvent]:
    if not task_ids:
        return []
    query = db.query(AnalysisTaskEvent).filter(AnalysisTaskEvent.task_id.in_(list(task_ids)))
    if event_type:
        query = query.filter(AnalysisTaskEvent.event_type == event_type)
    return query.order_by(AnalysisTaskEvent.task_id.asc(), AnalysisTaskEvent.created_at.asc()).all()
