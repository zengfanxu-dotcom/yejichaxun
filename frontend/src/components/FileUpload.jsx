import { useState } from "react";
import { TASK_STATUS, TERMINAL_STATUSES } from "../constants/taskState";

const API_BASE = "http://127.0.0.1:8000/api/v1";
const WS_BASE = API_BASE.replace(/^http/i, "ws");
const POLL_INTERVAL_MS = 1500;
const POLL_MAX_TIMES = 240;
const WS_WAIT_TIMEOUT_MS = POLL_INTERVAL_MS * POLL_MAX_TIMES;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatTaskError(task) {
  const code = task?.error_code ? `[${task.error_code}] ` : "";
  const message = task?.error_message || "分析失败，请稍后重试";
  return `${code}${message}`;
}

async function parseErrorResponse(response) {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    if (typeof data?.detail?.error_message === "string") {
      const code = data?.detail?.error_code ? `[${data.detail.error_code}] ` : "";
      return `${code}${data.detail.error_message}`;
    }
    return JSON.stringify(data);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

export default function FileUpload({ onResult, onLoading, onError }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  // 文件大小格式化函数
  const formatFileSize = (size) => {
    if (size < 1024) return size + " B";
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB";
    return (size / (1024 * 1024)).toFixed(1) + " MB";
  };

  const createTask = async (formData) => {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const errMsg = await parseErrorResponse(response);
      throw new Error(`上传失败：${errMsg}`);
    }
    const payload = await response.json();
    if (!payload?.task_id) {
      throw new Error("上传成功但未返回 task_id");
    }
    return payload.task_id;
  };

  const startAnalyze = async (taskId) => {
    const response = await fetch(`${API_BASE}/analyze/${taskId}`, {
      method: "POST",
    });
    if (!response.ok) {
      const errMsg = await parseErrorResponse(response);
      throw new Error(`分析请求失败：${errMsg}`);
    }
    return response.json();
  };

  const fetchTaskStatus = async (taskId) => {
    const response = await fetch(`${API_BASE}/tasks/${taskId}`);
    if (!response.ok) {
      const errMsg = await parseErrorResponse(response);
      throw new Error(`查询任务状态失败：${errMsg}`);
    }
    return response.json();
  };

  const pollTaskUntilFinished = async (taskId) => {
    let lastStateKey = "";
    for (let i = 0; i < POLL_MAX_TIMES; i += 1) {
      const task = await fetchTaskStatus(taskId);
      const stateKey = `${task.status}|${task.current_stage}|${task.progress}`;
      if (stateKey !== lastStateKey) {
        onLoading({
          isLoading: task.status === TASK_STATUS.QUEUED || task.status === TASK_STATUS.RUNNING,
          stage: task.current_stage || "upload",
          progress: Number(task.progress ?? 0),
          message: "",
          taskStatus: task.status,
        });
        lastStateKey = stateKey;
      }
      if (TERMINAL_STATUSES.has(task.status)) {
        return task;
      }
      await sleep(POLL_INTERVAL_MS);
    }
    throw new Error("任务轮询超时，请稍后在历史记录中查看结果");
  };

  const fetchReport = async (taskId) => {
    const response = await fetch(`${API_BASE}/report/${taskId}`);
    if (!response.ok) {
      const errMsg = await parseErrorResponse(response);
      throw new Error(`获取分析结果失败：${errMsg}`);
    }
    return response.json();
  };

  const waitTaskByWebSocket = async (taskId) =>
    new Promise((resolve, reject) => {
      let settled = false;
      let ws = null;
      const timeout = setTimeout(() => {
        if (settled) return;
        settled = true;
        if (ws && ws.readyState === WebSocket.OPEN) ws.close();
        reject(new Error("WebSocket 等待超时"));
      }, WS_WAIT_TIMEOUT_MS);

      const done = (nextTask, error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeout);
        if (ws && ws.readyState === WebSocket.OPEN) ws.close();
        if (error) reject(error);
        else resolve(nextTask);
      };

      try {
        ws = new WebSocket(`${WS_BASE}/ws/tasks/${taskId}`);
      } catch (err) {
        done(null, err instanceof Error ? err : new Error("WebSocket 初始化失败"));
        return;
      }

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data || "{}");
          if (payload?.type === "error") {
            done(null, new Error(payload.detail || "WebSocket 任务订阅失败"));
            return;
          }
          const task = payload?.task;
          if (!task?.task_id) return;

          onLoading({
            isLoading: task.status === TASK_STATUS.QUEUED || task.status === TASK_STATUS.RUNNING,
            stage: task.current_stage || "upload",
            progress: Number(task.progress ?? 0),
            message: "",
            taskStatus: task.status,
          });

          if (TERMINAL_STATUSES.has(task.status)) {
            done(task, null);
          }
        } catch {
          done(null, new Error("WebSocket 返回数据解析失败"));
        }
      };

      ws.onerror = () => {
        done(null, new Error("WebSocket 连接失败"));
      };

      ws.onclose = () => {
        if (settled) return;
        done(null, new Error("WebSocket 连接关闭"));
      };
    });

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    onLoading({
      isLoading: true,
      stage: "upload",
      progress: 5,
      message: "正在上传文件...",
      taskStatus: TASK_STATUS.QUEUED,
    });

    const formData = new FormData();
    formData.append("file", file);

    try {
      const taskId = await createTask(formData);
      onLoading({
        isLoading: true,
        stage: "upload",
        progress: 10,
        message: "文件上传成功，准备开始分析...",
        taskStatus: TASK_STATUS.QUEUED,
      });
      await startAnalyze(taskId);
      let task;
      try {
        task = await waitTaskByWebSocket(taskId);
      } catch (wsError) {
        console.warn("WebSocket 不可用，回退轮询:", wsError);
        task = await pollTaskUntilFinished(taskId);
      }

      if (task.status === TASK_STATUS.FAILED || task.status === TASK_STATUS.CANCELLED) {
        onError(formatTaskError(task));
      } else {
        const report = await fetchReport(taskId);
        onResult(report.result ?? null);
      }
    } catch (error) {
      console.error("上传失败:", error);
      onError(error.message || "文件分析失败，请重试");
    } finally {
      setLoading(false);
      onLoading(false);
    }
  };

  return (
    <section className="upload-card">
      <h2 className="upload-title">选择待分析文件</h2>
      <p className="upload-hint">支持 PDF、JPG、PNG 格式，建议上传清晰文件以提升识别效果。</p>

      <label className="file-input-wrap">
        <input
          className="file-input"
          type="file"
          accept="application/pdf,image/png,image/jpeg"
          onChange={(e) => {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
          }}
        />
      </label>

      {file && (
        <div className="file-meta">
          <p><strong>文件名：</strong>{file.name}</p>
          <p><strong>文件大小：</strong>{formatFileSize(file.size)}</p>
        </div>
      )}

      <button className="primary-btn upload-btn" onClick={handleUpload} disabled={loading || !file}>
        {loading ? "分析中..." : "上传并分析"}
      </button>
    </section>
  );
}