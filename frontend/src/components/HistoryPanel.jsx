import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CANCELLABLE_STATUSES,
  getStatusLabel,
  REPORT_VIEWABLE_STATUSES,
  RETRYABLE_STATUSES,
  TASK_STATUS,
} from "../constants/taskState";

const API_BASE = "http://127.0.0.1:8000/api/v1";
const AUTO_REFRESH_MS = 5 * 60 * 1000;

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function toErrorText(err) {
  if (err instanceof Error && err.message) return err.message;
  return "加载历史任务失败";
}

async function parseErrorResponse(response) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") return payload.detail;
    if (typeof payload?.detail?.error_message === "string") {
      const code = payload.detail.error_code ? `[${payload.detail.error_code}] ` : "";
      return `${code}${payload.detail.error_message}`;
    }
    return JSON.stringify(payload);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

function statusText(status) {
  return getStatusLabel(status);
}

function stageText(stage) {
  if (stage === "upload") return "上传";
  if (stage === "ocr") return "OCR";
  if (stage === "rag") return "RAG";
  if (stage === "llm") return "LLM";
  if (stage === "postprocess") return "后处理";
  if (stage === "done") return "完成";
  return stage || "未知";
}

function eventTypeText(eventType) {
  if (eventType === "created") return "创建";
  if (eventType === "status") return "状态";
  if (eventType === "stage") return "阶段";
  if (eventType === "error") return "异常";
  if (eventType === "retry") return "重试";
  return eventType || "事件";
}

function formatDuration(ms) {
  const value = Number(ms || 0);
  if (!Number.isFinite(value) || value <= 0) return "—";
  if (value < 1000) return `${value}ms`;
  const sec = value / 1000;
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const min = Math.floor(sec / 60);
  const left = Math.round(sec % 60);
  return `${min}m ${left}s`;
}

function formatPercent(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return "0.0%";
  return `${(num * 100).toFixed(1)}%`;
}

export default function HistoryPanel({ onSelectReport, onError }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewingTaskId, setViewingTaskId] = useState(null);
  const [actioningTaskId, setActioningTaskId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [detailTask, setDetailTask] = useState(null);
  const [detailEvents, setDetailEvents] = useState([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailDurations, setDetailDurations] = useState({});
  const [detailTotalDuration, setDetailTotalDuration] = useState(0);
  const [metrics, setMetrics] = useState(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/tasks?limit=10&offset=0`);
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      const data = await response.json();
      const nextTasks = Array.isArray(data?.items) ? data.items : [];
      setTasks(nextTasks);
      if (detailTask?.task_id) {
        const latestTask = nextTasks.find((item) => item.task_id === detailTask.task_id);
        if (latestTask) setDetailTask(latestTask);
      }
    } catch (err) {
      onError?.(`历史任务加载失败：${toErrorText(err)}`);
    } finally {
      setLoading(false);
    }
  }, [detailTask?.task_id, onError]);

  const loadMetrics = useCallback(async () => {
    setMetricsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/tasks/metrics?limit=100`);
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      const payload = await response.json();
      setMetrics(payload || null);
    } catch (err) {
      onError?.(`加载诊断指标失败：${toErrorText(err)}`);
    } finally {
      setMetricsLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    loadTasks();
    loadMetrics();
    const timer = setInterval(loadTasks, AUTO_REFRESH_MS);
    return () => clearInterval(timer);
  }, [loadMetrics, loadTasks]);

  const filteredTasks = useMemo(() => {
    if (statusFilter === "all") return tasks;
    return tasks.filter((task) => task.status === statusFilter);
  }, [statusFilter, tasks]);

  const emptyText = useMemo(() => {
    if (loading) return "历史任务加载中...";
    if (!tasks.length) return "暂无历史任务";
    if (!filteredTasks.length) return "当前筛选条件下暂无任务";
    return "";
  }, [filteredTasks.length, loading, tasks.length]);

  const handleViewReport = async (task) => {
    if (!task?.task_id) return;
    setViewingTaskId(task.task_id);
    try {
      const response = await fetch(`${API_BASE}/report/${task.task_id}`);
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }

      const payload = await response.json();
      if (payload?.result) {
        onSelectReport?.(payload.result);
        return;
      }

      if (payload?.status === TASK_STATUS.FAILED) {
        const code = payload?.error_code ? `[${payload.error_code}] ` : "";
        onError?.(`${code}${payload?.error_message || "任务执行失败"}`);
        return;
      }

      onError?.("当前任务暂无可展示结果");
    } catch (err) {
      onError?.(`查看报告失败：${toErrorText(err)}`);
    } finally {
      setViewingTaskId(null);
    }
  };

  const handleRetryAnalyze = async (task) => {
    if (!task?.task_id) return;
    setActioningTaskId(task.task_id);
    try {
      const response = await fetch(`${API_BASE}/analyze/${task.task_id}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      await loadTasks();
      await loadMetrics();
    } catch (err) {
      onError?.(`重新分析失败：${toErrorText(err)}`);
    } finally {
      setActioningTaskId(null);
    }
  };

  const handleCancelTask = async (task) => {
    if (!task?.task_id) return;
    setActioningTaskId(task.task_id);
    try {
      const response = await fetch(`${API_BASE}/tasks/${task.task_id}/cancel`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      await loadTasks();
      await loadMetrics();
    } catch (err) {
      onError?.(`取消任务失败：${toErrorText(err)}`);
    } finally {
      setActioningTaskId(null);
    }
  };

  const handleOpenTaskDetail = async (task) => {
    if (!task?.task_id) return;
    setDetailTask(task);
    setDetailEvents([]);
    setDetailError("");
    setDetailLoading(true);
    setDetailDurations({});
    setDetailTotalDuration(0);
    try {
      const response = await fetch(`${API_BASE}/tasks/${task.task_id}/events?limit=100&offset=0`);
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      const payload = await response.json();
      setDetailEvents(Array.isArray(payload?.items) ? payload.items : []);
      setDetailDurations(payload?.stage_durations_ms || {});
      setDetailTotalDuration(Number(payload?.total_duration_ms || 0));
    } catch (err) {
      const message = `加载任务详情失败：${toErrorText(err)}`;
      setDetailError(message);
      onError?.(message);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseTaskDetail = () => {
    setDetailTask(null);
    setDetailEvents([]);
    setDetailError("");
    setDetailLoading(false);
    setDetailDurations({});
    setDetailTotalDuration(0);
  };

  const copyTaskId = async () => {
    if (!detailTask?.task_id) return;
    try {
      await navigator.clipboard.writeText(detailTask.task_id);
    } catch {
      onError?.("复制 task_id 失败，请手动复制");
    }
  };

  return (
    <section className="history-card">
      <div className="history-header">
        <h2 className="history-title">历史任务（最近 10 条）</h2>
        <div className="history-actions">
          <select
            className="history-filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">全部状态</option>
            <option value={TASK_STATUS.QUEUED}>排队中</option>
            <option value={TASK_STATUS.RUNNING}>运行中</option>
            <option value={TASK_STATUS.SUCCEEDED}>成功</option>
            <option value={TASK_STATUS.FAILED}>失败</option>
            <option value={TASK_STATUS.CANCELLED}>已取消</option>
          </select>
          <button className="primary-btn history-refresh-btn" onClick={loadTasks} disabled={loading}>
            {loading ? "刷新中..." : "刷新"}
          </button>
          <button className="primary-btn history-refresh-btn" onClick={loadMetrics} disabled={metricsLoading}>
            {metricsLoading ? "统计中..." : "刷新指标"}
          </button>
        </div>
      </div>

      <div className="history-metrics-grid">
        <div className="history-metric-card">
          <p className="history-metric-title">样本任务</p>
          <p className="history-metric-value">{metrics?.window_size ?? 0}</p>
        </div>
        <div className="history-metric-card">
          <p className="history-metric-title">成功率</p>
          <p className="history-metric-value">{formatPercent(metrics?.success_rate)}</p>
        </div>
        <div className="history-metric-card">
          <p className="history-metric-title">失败率</p>
          <p className="history-metric-value">{formatPercent(metrics?.failure_rate)}</p>
        </div>
        <div className="history-metric-card">
          <p className="history-metric-title">重试成功率</p>
          <p className="history-metric-value">{formatPercent(metrics?.retry?.retried_success_rate)}</p>
        </div>
      </div>
      {!!metrics?.failure_code_counts && (
        <p className="history-meta">
          失败分布：
          {Object.entries(metrics.failure_code_counts)
            .map(([code, count]) => `${code}:${count}`)
            .join(" | ") || "—"}
        </p>
      )}
      {!!metrics?.avg_stage_duration_ms && (
        <p className="history-meta">
          阶段均耗：
          OCR {formatDuration(metrics.avg_stage_duration_ms.ocr)} | RAG{" "}
          {formatDuration(metrics.avg_stage_duration_ms.rag)} | LLM{" "}
          {formatDuration(metrics.avg_stage_duration_ms.llm)} | 后处理{" "}
          {formatDuration(metrics.avg_stage_duration_ms.postprocess)}
        </p>
      )}

      {emptyText ? (
        <p className="history-empty">{emptyText}</p>
      ) : (
        <div className="history-list">
          {filteredTasks.map((task) => {
            const disableView = !REPORT_VIEWABLE_STATUSES.has(task.status);
            return (
              <div className="history-item" key={task.task_id}>
                <div className="history-item-main">
                  <p className="history-file-name">{task.file_name || "未知文件"}</p>
                  <p className="history-meta">
                    任务ID：{task.task_id}
                  </p>
                  <p className="history-meta">
                    状态：{statusText(task.status)} | 阶段：{task.current_stage || "—"} | 进度：{task.progress ?? 0}%
                  </p>
                  <p className="history-meta">
                    创建时间：{formatDateTime(task.created_at)}
                  </p>
                </div>
                <div className="history-item-actions">
                  <button
                    className="primary-btn history-detail-btn"
                    disabled={detailLoading && detailTask?.task_id === task.task_id}
                    onClick={() => handleOpenTaskDetail(task)}
                  >
                    {detailLoading && detailTask?.task_id === task.task_id ? "加载中..." : "任务详情"}
                  </button>
                  <button
                    className="primary-btn history-view-btn"
                    disabled={disableView || viewingTaskId === task.task_id}
                    onClick={() => handleViewReport(task)}
                  >
                    {viewingTaskId === task.task_id ? "加载中..." : "查看报告"}
                  </button>
                  {RETRYABLE_STATUSES.has(task.status) && (
                    <button
                      className="primary-btn history-retry-btn"
                      disabled={actioningTaskId === task.task_id}
                      onClick={() => handleRetryAnalyze(task)}
                    >
                      {actioningTaskId === task.task_id ? "处理中..." : "重新分析"}
                    </button>
                  )}
                  {CANCELLABLE_STATUSES.has(task.status) && (
                    <button
                      className="primary-btn history-cancel-btn"
                      disabled={actioningTaskId === task.task_id}
                      onClick={() => handleCancelTask(task)}
                    >
                      {actioningTaskId === task.task_id ? "处理中..." : "取消任务"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {detailTask && (
        <div className="history-detail-mask" onClick={handleCloseTaskDetail}>
          <aside className="history-detail-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="history-detail-header">
              <h3 className="history-detail-title">任务详情</h3>
              <div className="history-detail-header-actions">
                <button className="history-detail-copy-btn" onClick={copyTaskId}>
                  复制 task_id
                </button>
                <button className="history-detail-close-btn" onClick={handleCloseTaskDetail}>
                  关闭
                </button>
              </div>
            </div>
            <div className="history-detail-body">
              <p className="history-meta">任务ID：{detailTask.task_id}</p>
              <p className="history-meta">文件名：{detailTask.file_name || "未知文件"}</p>
              <p className="history-meta">状态：{statusText(detailTask.status)}</p>
              <p className="history-meta">
                当前阶段：{stageText(detailTask.current_stage)} | 进度：{detailTask.progress ?? 0}%
              </p>
              <p className="history-meta">创建时间：{formatDateTime(detailTask.created_at)}</p>
              <p className="history-meta">开始时间：{formatDateTime(detailTask.started_at)}</p>
              <p className="history-meta">结束时间：{formatDateTime(detailTask.finished_at)}</p>
              <p className="history-meta">总耗时：{formatDuration(detailTotalDuration)}</p>

              <h4 className="history-detail-subtitle">阶段耗时</h4>
              <p className="history-meta">
                OCR：{formatDuration(detailDurations?.ocr)} | RAG：{formatDuration(detailDurations?.rag)} | LLM：
                {formatDuration(detailDurations?.llm)} | 后处理：{formatDuration(detailDurations?.postprocess)}
              </p>

              <h4 className="history-detail-subtitle">阶段日志</h4>
              {detailLoading ? (
                <p className="history-empty">详情加载中...</p>
              ) : detailError ? (
                <p className="history-empty">{detailError}</p>
              ) : !detailEvents.length ? (
                <p className="history-empty">暂无阶段日志</p>
              ) : (
                <div className="history-event-list">
                  {detailEvents.map((event) => (
                    <div
                      className={`history-event-item ${
                        event.event_type === "error" ? "history-event-item-error" : ""
                      }`}
                      key={event.event_id}
                    >
                      <p className="history-meta">
                        [{eventTypeText(event.event_type)}] {stageText(event.stage)} | {event.progress ?? 0}%
                      </p>
                      <p className="history-meta">{event.message || "—"}</p>
                      <p className="history-meta">{formatDateTime(event.created_at)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </aside>
        </div>
      )}
    </section>
  );
}
