import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FileUpload from "./FileUpload";

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "ERROR",
    json: async () => payload,
  };
}

class MockWebSocket {
  static instances = [];
  static OPEN = 1;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.OPEN;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    MockWebSocket.instances.push(this);
  }

  emitMessage(payload) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  emitError() {
    this.onerror?.(new Event("error"));
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new Event("close"));
  }
}

describe("FileUpload key flows", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    global.WebSocket = MockWebSocket;
    global.fetch = jest.fn();
  });

  test("upload -> analyze -> report succeeds via websocket", async () => {
    const onResult = jest.fn();
    const onLoading = jest.fn();
    const onError = jest.fn();

    global.fetch.mockImplementation((url, options) => {
      if (url.endsWith("/upload")) return Promise.resolve(jsonResponse({ task_id: "task-1" }));
      if (url.endsWith("/analyze/task-1") && options?.method === "POST") {
        return Promise.resolve(jsonResponse({ task_id: "task-1", status: "running" }));
      }
      if (url.endsWith("/report/task-1")) {
        return Promise.resolve(jsonResponse({ task_id: "task-1", status: "succeeded", result: { ok: true } }));
      }
      return Promise.reject(new Error(`unexpected url: ${url}`));
    });

    render(<FileUpload onResult={onResult} onLoading={onLoading} onError={onError} />);

    const file = new File(["hello"], "demo.pdf", { type: "application/pdf" });
    const fileInput = document.querySelector("input[type='file']");
    expect(fileInput).not.toBeNull();
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByRole("button", { name: "上传并分析" }));

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    const ws = MockWebSocket.instances[0];

    act(() => {
      ws.emitMessage({
        type: "task.snapshot",
        task: {
          task_id: "task-1",
          status: "running",
          current_stage: "ocr",
          progress: 15,
        },
      });
      ws.emitMessage({
        type: "task.update",
        task: {
          task_id: "task-1",
          status: "succeeded",
          current_stage: "done",
          progress: 100,
        },
      });
    });

    await waitFor(() => expect(onResult).toHaveBeenCalledWith({ ok: true }));
    expect(onError).not.toHaveBeenCalled();
  });

  test("websocket failure falls back to polling", async () => {
    const onResult = jest.fn();
    const onLoading = jest.fn();
    const onError = jest.fn();

    global.fetch.mockImplementation((url, options) => {
      if (url.endsWith("/upload")) return Promise.resolve(jsonResponse({ task_id: "task-2" }));
      if (url.endsWith("/analyze/task-2") && options?.method === "POST") {
        return Promise.resolve(jsonResponse({ task_id: "task-2", status: "running" }));
      }
      if (url.endsWith("/tasks/task-2")) {
        return Promise.resolve(
          jsonResponse({
            task_id: "task-2",
            status: "succeeded",
            current_stage: "done",
            progress: 100,
          })
        );
      }
      if (url.endsWith("/report/task-2")) {
        return Promise.resolve(jsonResponse({ task_id: "task-2", status: "succeeded", result: { from: "poll" } }));
      }
      return Promise.reject(new Error(`unexpected url: ${url}`));
    });

    render(<FileUpload onResult={onResult} onLoading={onLoading} onError={onError} />);

    const file = new File(["world"], "demo2.pdf", { type: "application/pdf" });
    const fileInput = document.querySelector("input[type='file']");
    expect(fileInput).not.toBeNull();
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByRole("button", { name: "上传并分析" }));

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    act(() => {
      MockWebSocket.instances[0].emitError();
    });

    await waitFor(() => expect(onResult).toHaveBeenCalledWith({ from: "poll" }));
    expect(onError).not.toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/tasks/task-2");
  });
});
