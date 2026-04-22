# Task State Machine Rules

This document defines the single source of truth for task status transitions.

## Statuses

- `queued`: uploaded and waiting to run.
- `running`: analysis pipeline is executing.
- `succeeded`: analysis finished and report is ready.
- `failed`: analysis finished with an error.
- `cancelled`: task was cancelled by user.

## Transition Rules

- `queued -> running`: when `POST /analyze/{task_id}` starts.
- `running -> succeeded`: when pipeline completes and result is persisted.
- `running -> failed`: when pipeline throws an exception.
- `queued/running -> cancelled`: when `POST /tasks/{task_id}/cancel` is called.
- `cancelled -> queued`: when `POST /analyze/{task_id}` is called again.

## Operation Rules

- Cancellable statuses: `queued`, `running`
- Retryable statuses: `failed`, `cancelled`
- Report viewable statuses: `succeeded`, `failed`

## Code Reference

- Backend constants: `backend/app/core/task_state.py`
- Frontend constants: `frontend/src/constants/taskState.js`
