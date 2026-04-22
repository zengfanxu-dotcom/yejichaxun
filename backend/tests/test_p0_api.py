import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from starlette.websockets import WebSocketDisconnect

from backend.app.api.v1.endpoints import analyze as analyze_endpoint
from backend.app.core.task_state import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
)
from backend.app.db.models import AnalysisResult, AnalysisTask, AnalysisTaskEvent


def _seed_task(
    db_session_factory,
    *,
    status=STATUS_QUEUED,
    current_stage="upload",
    progress=5,
    error_code=None,
    error_message=None,
):
    db = db_session_factory()
    try:
        now = datetime.now(timezone.utc)
        task = AnalysisTask(
            id=str(uuid4()),
            status=status,
            current_stage=current_stage,
            progress=progress,
            file_name="mock.pdf",
            file_size=128,
            file_path="F:/tmp/mock.pdf",
            content_type="application/pdf",
            error_code=error_code,
            error_message=error_message,
            created_at=now,
            started_at=now if status in (STATUS_RUNNING, STATUS_SUCCEEDED, STATUS_FAILED, STATUS_CANCELLED) else None,
            finished_at=now if status in (STATUS_SUCCEEDED, STATUS_FAILED, STATUS_CANCELLED) else None,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.id
    finally:
        db.close()


def test_upload_creates_task(client, db_session_factory):
    response = client.post(
        "/api/v1/upload",
        files={"file": ("demo.pdf", b"fake-content", "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == STATUS_QUEUED
    assert payload["current_stage"] == "upload"
    assert payload["progress"] == 5

    db = db_session_factory()
    try:
        task = db.query(AnalysisTask).filter(AnalysisTask.id == payload["task_id"]).first()
        assert task is not None
        assert task.file_name == "demo.pdf"
    finally:
        db.close()


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/v1/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "空文件无法分析"


def test_analyze_rejects_running_task(client, db_session_factory):
    task_id = _seed_task(
        db_session_factory,
        status=STATUS_RUNNING,
        current_stage="ocr",
        progress=20,
    )
    response = client.post(f"/api/v1/analyze/{task_id}")
    assert response.status_code == 409
    assert response.json()["detail"] == "task 正在运行"


def test_analyze_second_request_conflicts(client, db_session_factory, monkeypatch):
    task_id = _seed_task(db_session_factory, status=STATUS_QUEUED, current_stage="upload", progress=5)
    monkeypatch.setattr(analyze_endpoint, "_run_analysis_pipeline", lambda _: None)

    first = client.post(f"/api/v1/analyze/{task_id}")
    second = client.post(f"/api/v1/analyze/{task_id}")

    assert first.status_code == 200
    assert first.json()["status"] == STATUS_RUNNING
    assert second.status_code == 409


def test_analyze_allows_retry_for_cancelled_task(client, db_session_factory, monkeypatch):
    task_id = _seed_task(
        db_session_factory,
        status=STATUS_CANCELLED,
        current_stage="done",
        progress=100,
        error_code="TASK_CANCELLED",
        error_message="用户取消",
    )
    monkeypatch.setattr(analyze_endpoint, "_run_analysis_pipeline", lambda _: None)

    response = client.post(f"/api/v1/analyze/{task_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == STATUS_RUNNING
    assert payload["current_stage"] == "ocr"

    db = db_session_factory()
    try:
        retry_events = (
            db.query(AnalysisTaskEvent)
            .filter(
                AnalysisTaskEvent.task_id == task_id,
                AnalysisTaskEvent.event_type == "retry",
            )
            .all()
        )
        assert len(retry_events) == 1
    finally:
        db.close()


def test_cancel_endpoint_state_machine(client, db_session_factory):
    running_task_id = _seed_task(
        db_session_factory,
        status=STATUS_RUNNING,
        current_stage="rag",
        progress=55,
    )
    success_task_id = _seed_task(
        db_session_factory,
        status=STATUS_SUCCEEDED,
        current_stage="done",
        progress=100,
    )

    ok_resp = client.post(f"/api/v1/tasks/{running_task_id}/cancel")
    assert ok_resp.status_code == 200
    assert ok_resp.json()["status"] == STATUS_CANCELLED

    conflict_resp = client.post(f"/api/v1/tasks/{success_task_id}/cancel")
    assert conflict_resp.status_code == 409
    assert "不可取消" in conflict_resp.json()["detail"]


def test_report_endpoint_for_succeeded_and_failed_tasks(client, db_session_factory):
    failed_task_id = _seed_task(
        db_session_factory,
        status=STATUS_FAILED,
        current_stage="done",
        progress=100,
        error_code="OCR_FAILED",
        error_message="ocr error",
    )
    succeeded_task_id = _seed_task(
        db_session_factory,
        status=STATUS_SUCCEEDED,
        current_stage="done",
        progress=100,
    )

    db = db_session_factory()
    try:
        db.add(
            AnalysisResult(
                task_id=succeeded_task_id,
                review_status="通过",
                total_score=86.5,
                valid_count=2,
                invalid_count=1,
                result_json=json.dumps({"结论": "通过"}, ensure_ascii=False),
                rag_context="context",
            )
        )
        db.commit()
    finally:
        db.close()

    failed_resp = client.get(f"/api/v1/report/{failed_task_id}")
    assert failed_resp.status_code == 200
    assert failed_resp.json()["status"] == STATUS_FAILED
    assert failed_resp.json()["result"] is None

    success_resp = client.get(f"/api/v1/report/{succeeded_task_id}")
    assert success_resp.status_code == 200
    assert success_resp.json()["status"] == STATUS_SUCCEEDED
    assert success_resp.json()["result"]["结论"] == "通过"


def test_events_and_metrics_endpoints(client, db_session_factory):
    succeeded_task_id = _seed_task(
        db_session_factory,
        status=STATUS_SUCCEEDED,
        current_stage="done",
        progress=100,
    )
    failed_task_id = _seed_task(
        db_session_factory,
        status=STATUS_FAILED,
        current_stage="done",
        progress=100,
        error_code="OCR_FAILED",
        error_message="ocr fail",
    )

    base_time = datetime.now(timezone.utc)
    db = db_session_factory()
    try:
        db.add_all(
            [
                AnalysisTaskEvent(
                    task_id=succeeded_task_id,
                    stage="ocr",
                    event_type="status",
                    message="start ocr",
                    progress=15,
                    created_at=base_time,
                ),
                AnalysisTaskEvent(
                    task_id=succeeded_task_id,
                    stage="rag",
                    event_type="stage",
                    message="start rag",
                    progress=55,
                    created_at=base_time + timedelta(seconds=2),
                ),
                AnalysisTaskEvent(
                    task_id=succeeded_task_id,
                    stage="done",
                    event_type="status",
                    message="done",
                    progress=100,
                    created_at=base_time + timedelta(seconds=4),
                ),
                AnalysisTaskEvent(
                    task_id=succeeded_task_id,
                    stage="upload",
                    event_type="retry",
                    message="retry",
                    progress=5,
                    created_at=base_time + timedelta(seconds=1),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    events_resp = client.get(f"/api/v1/tasks/{succeeded_task_id}/events?limit=100&offset=0")
    assert events_resp.status_code == 200
    events_payload = events_resp.json()
    assert events_payload["total_duration_ms"] >= 0
    assert "ocr" in events_payload["stage_durations_ms"]

    metrics_resp = client.get("/api/v1/tasks/metrics?limit=100")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["window_size"] >= 2
    assert metrics["status_counts"][STATUS_SUCCEEDED] >= 1
    assert metrics["status_counts"][STATUS_FAILED] >= 1
    assert metrics["failure_code_counts"]["OCR_FAILED"] >= 1
    assert metrics["retry"]["retried_task_count"] >= 1


def test_ws_task_snapshot_and_missing_task(client, db_session_factory):
    task_id = _seed_task(
        db_session_factory,
        status=STATUS_QUEUED,
        current_stage="upload",
        progress=5,
    )

    with client.websocket_connect(f"/api/v1/ws/tasks/{task_id}") as ws:
        payload = ws.receive_json()
        assert payload["type"] == "task.snapshot"
        assert payload["task"]["task_id"] == task_id

    with client.websocket_connect("/api/v1/ws/tasks/not-found") as ws:
        error_payload = ws.receive_json()
        assert error_payload["type"] == "error"
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()
