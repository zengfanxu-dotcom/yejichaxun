import React from 'react';
import { Spin, Typography } from 'antd';
import { TASK_STATUS } from "../constants/taskState";

const { Text } = Typography;

const stageLabelMap = {
  upload: "正在上传文件",
  ocr: "正在 OCR 识别",
  rag: "正在检索匹配",
  llm: "正在评审计算",
  postprocess: "正在整理结果",
  done: "分析已完成",
};

const LoadingComponent = ({
  stage = "upload",
  progress = 0,
  taskStatus = TASK_STATUS.RUNNING,
  message = "",
}) => {
  const stageLabel = stageLabelMap[stage] || "分析中";
  const safeProgress = Number.isFinite(progress) ? Math.max(0, Math.min(100, Math.round(progress))) : 0;
  const statusLabel = taskStatus === TASK_STATUS.QUEUED ? "（排队中）" : "";
  const text = message || `${stageLabel}${statusLabel} ${safeProgress}%`;

  return (
    <div className="loading-container">
      <Spin size="large" />
      <div className="loading-content">
        <Text type="secondary" className="loading-text">
          {text}
        </Text>
        <div className="loading-progress-track">
          <div
            className="loading-progress-bar"
            style={{ width: `${safeProgress}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default LoadingComponent;