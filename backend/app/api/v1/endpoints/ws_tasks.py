from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.core.realtime.task_stream import send_task_snapshot, task_stream_broker
from backend.app.db.repositories.task_repo import get_task
from backend.app.db.session import SessionLocal

router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def task_updates_ws(websocket: WebSocket, task_id: str) -> None:
    await task_stream_broker.connect(task_id, websocket)
    db = SessionLocal()
    try:
        task = get_task(db, task_id)
        if not task:
            await websocket.send_json({"type": "error", "detail": "task 不存在", "task_id": task_id})
            await websocket.close(code=4404)
            return
        await send_task_snapshot(task_id, websocket.send_json, task)

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await task_stream_broker.disconnect(task_id, websocket)
        db.close()
