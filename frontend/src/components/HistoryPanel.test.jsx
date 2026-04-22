import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import HistoryPanel from "./HistoryPanel";

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "ERROR",
    json: async () => payload,
  };
}

const baseMetrics = {
  window_size: 1,
  success_rate: 1,
  failure_rate: 0,
  failure_code_counts: {},
  retry: { retried_task_count: 0, retried_success_count: 0, retried_success_rate: 0 },
  avg_stage_duration_ms: {},
};

describe("HistoryPanel key flows", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  test("cancelled task supports retry analyze", async () => {
    const onError = jest.fn();
    const onSelectReport = jest.fn();

    global.fetch.mockImplementation((url, options) => {
      if (url.includes("/tasks?limit=10&offset=0")) {
        return Promise.resolve(
          jsonResponse({
            items: [
              {
                task_id: "task-cancelled",
                status: "cancelled",
                current_stage: "done",
                progress: 100,
                file_name: "c.pdf",
                created_at: new Date().toISOString(),
              },
            ],
          })
        );
      }
      if (url.includes("/tasks/metrics?limit=100")) {
        return Promise.resolve(jsonResponse(baseMetrics));
      }
      if (url.includes("/analyze/task-cancelled") && options?.method === "POST") {
        return Promise.resolve(jsonResponse({ task_id: "task-cancelled", status: "running" }));
      }
      return Promise.reject(new Error(`unexpected url: ${url}`));
    });

    render(<HistoryPanel onError={onError} onSelectReport={onSelectReport} />);

    const retryButton = await screen.findByRole("button", { name: "重新分析" });
    await userEvent.click(retryButton);

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        "http://127.0.0.1:8000/api/v1/analyze/task-cancelled",
        { method: "POST" }
      )
    );
    expect(onError).not.toHaveBeenCalled();
  });

  test("running task supports cancel action", async () => {
    const onError = jest.fn();
    const onSelectReport = jest.fn();

    global.fetch.mockImplementation((url, options) => {
      if (url.includes("/tasks?limit=10&offset=0")) {
        return Promise.resolve(
          jsonResponse({
            items: [
              {
                task_id: "task-running",
                status: "running",
                current_stage: "rag",
                progress: 50,
                file_name: "r.pdf",
                created_at: new Date().toISOString(),
              },
            ],
          })
        );
      }
      if (url.includes("/tasks/metrics?limit=100")) {
        return Promise.resolve(jsonResponse(baseMetrics));
      }
      if (url.includes("/tasks/task-running/cancel") && options?.method === "POST") {
        return Promise.resolve(jsonResponse({ task_id: "task-running", status: "cancelled" }));
      }
      return Promise.reject(new Error(`unexpected url: ${url}`));
    });

    render(<HistoryPanel onError={onError} onSelectReport={onSelectReport} />);

    const cancelButton = await screen.findByRole("button", { name: "取消任务" });
    await userEvent.click(cancelButton);

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        "http://127.0.0.1:8000/api/v1/tasks/task-running/cancel",
        { method: "POST" }
      )
    );
    expect(onError).not.toHaveBeenCalled();
  });
});
