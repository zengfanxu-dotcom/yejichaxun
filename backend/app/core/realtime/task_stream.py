from __future__ import annotations

import asyncio
import threading
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket


def task_to_payload(task: Any) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "status": task.status,
        "current_stage": task.current_stage,
        "progress": task.progress,
        "error_code": task.error_code,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


class TaskStreamBroker:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections[task_id].add(websocket)
            self._loop = asyncio.get_running_loop()

    async def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        with self._lock:
            sockets = self._connections.get(task_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(task_id, None)

    async def _broadcast(self, task_id: str, message: dict[str, Any]) -> None:
        with self._lock:
            sockets = list(self._connections.get(task_id, set()))
        if not sockets:
            return

        dropped: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(message)
            except Exception:
                dropped.append(socket)

        if dropped:
            with self._lock:
                current = self._connections.get(task_id, set())
                for socket in dropped:
                    current.discard(socket)
                if not current:
                    self._connections.pop(task_id, None)

    def publish(self, task_id: str, message: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(task_id, message), loop)

    async def publish_async(self, task_id: str, message: dict[str, Any]) -> None:
        await self._broadcast(task_id, message)


task_stream_broker = TaskStreamBroker()


def publish_task_update(task: Any) -> None:
    task_stream_broker.publish(
        str(task.id),
        {
            "type": "task.update",
            "task": task_to_payload(task),
        },
    )


async def send_task_snapshot(task_id: str, sender: Callable[[dict[str, Any]], Awaitable[None]], task: Any) -> None:
    await sender(
        {
            "type": "task.snapshot",
            "task_id": task_id,
            "task": task_to_payload(task),
        }
    )
