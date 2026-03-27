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
    <div style={{ padding: "20px" }}>
      <h1>业绩匹配分析系统</h1>

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
  );
}

export default App;