import { useState } from "react";
import FileUpload from "./components/FileUpload";
import ResultDisplay from "./components/ResultDisplay";
import Loading from "./components/Loading";
import ErrorComponent from "./components/ErrorComponent";
import HistoryPanel from "./components/HistoryPanel";
import { TASK_STATUS } from "./constants/taskState";

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMeta, setLoadingMeta] = useState({
    stage: "upload",
    progress: 0,
    message: "分析中，请稍候...",
    taskStatus: TASK_STATUS.QUEUED,
  });
  const [error, setError] = useState(null);

  const handleResult = (resultData) => {
    setResult(resultData);
    setError(null);
    setLoading(false);
  };

  const handleLoading = (isLoading) => {
    if (typeof isLoading === "boolean") {
      setLoading(isLoading);
      return;
    }

    const nextLoading = isLoading?.isLoading !== false;
    setLoading(nextLoading);
    setLoadingMeta((prev) => ({
      ...prev,
      stage: isLoading?.stage ?? prev.stage,
      progress: Number(isLoading?.progress ?? prev.progress),
      message: isLoading?.message ?? prev.message,
      taskStatus: isLoading?.taskStatus ?? prev.taskStatus,
    }));
  };

  const handleError = (errorMessage) => {
    setError(errorMessage);
    setResult(null);
    setLoading(false);
  };

  const handleRetry = () => {
    setError(null);
    setResult(null);
  };

  return (
    <div className="app-shell">
      <div className="app-container">
        <h1 className="app-title">业绩匹配分析系统</h1>
        <p className="app-subtitle">上传招标文件，系统将自动完成 OCR、检索匹配与评审结果生成。</p>

        <FileUpload
          onResult={handleResult}
          onLoading={handleLoading}
          onError={handleError}
        />

        {loading && (
          <Loading
            stage={loadingMeta.stage}
            progress={loadingMeta.progress}
            message={loadingMeta.message}
            taskStatus={loadingMeta.taskStatus}
          />
        )}

        <ErrorComponent
          error={error}
          onRetry={handleRetry}
        />

        <HistoryPanel onSelectReport={handleResult} onError={handleError} />

        <ResultDisplay result={result} />
      </div>
    </div>
  );
}

export default App;