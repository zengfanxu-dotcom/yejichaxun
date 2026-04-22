export const TASK_STATUS = {
  QUEUED: "queued",
  RUNNING: "running",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
  CANCELLED: "cancelled",
};

export const TERMINAL_STATUSES = new Set([
  TASK_STATUS.SUCCEEDED,
  TASK_STATUS.FAILED,
  TASK_STATUS.CANCELLED,
]);

export const CANCELLABLE_STATUSES = new Set([
  TASK_STATUS.QUEUED,
  TASK_STATUS.RUNNING,
]);

export const RETRYABLE_STATUSES = new Set([
  TASK_STATUS.FAILED,
  TASK_STATUS.CANCELLED,
]);

export const REPORT_VIEWABLE_STATUSES = new Set([
  TASK_STATUS.SUCCEEDED,
  TASK_STATUS.FAILED,
]);

export const STATUS_LABEL = {
  [TASK_STATUS.SUCCEEDED]: "成功",
  [TASK_STATUS.FAILED]: "失败",
  [TASK_STATUS.RUNNING]: "运行中",
  [TASK_STATUS.QUEUED]: "排队中",
  [TASK_STATUS.CANCELLED]: "已取消",
};

export function getStatusLabel(status) {
  return STATUS_LABEL[status] || status || "未知";
}
