from typing import Final

STATUS_QUEUED: Final[str] = "queued"
STATUS_RUNNING: Final[str] = "running"
STATUS_SUCCEEDED: Final[str] = "succeeded"
STATUS_FAILED: Final[str] = "failed"
STATUS_CANCELLED: Final[str] = "cancelled"

TERMINAL_STATUSES: Final[set[str]] = {
    STATUS_SUCCEEDED,
    STATUS_FAILED,
    STATUS_CANCELLED,
}

CANCELLABLE_STATUSES: Final[set[str]] = {
    STATUS_QUEUED,
    STATUS_RUNNING,
}

RETRYABLE_STATUSES: Final[set[str]] = {
    STATUS_FAILED,
    STATUS_CANCELLED,
}

REPORT_READY_STATUSES: Final[set[str]] = {
    STATUS_SUCCEEDED,
}

REPORT_ACCESSIBLE_STATUSES: Final[set[str]] = {
    STATUS_SUCCEEDED,
    STATUS_FAILED,
}


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES


def is_cancellable(status: str) -> bool:
    return status in CANCELLABLE_STATUSES


def is_retryable(status: str) -> bool:
    return status in RETRYABLE_STATUSES


def can_fetch_report(status: str) -> bool:
    return status in REPORT_ACCESSIBLE_STATUSES
