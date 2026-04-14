import { useState } from "react";
import FileUpload from "./components/FileUpload";
import ResultDisplay from "./components/ResultDisplay";
import Loading from "./components/Loading";
import ErrorComponent from "./components/ErrorComponent";

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleResult = (resultData) => {
    setResult(resultData);
    setError(null);
    setLoading(false);
  };

  const handleLoading = (isLoading) => {
    setLoading(isLoading);
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

        {loading && <Loading />}

        <ErrorComponent
          error={error}
          onRetry={handleRetry}
        />

        <ResultDisplay result={result} />
      </div>
    </div>
  );
}

export default App;