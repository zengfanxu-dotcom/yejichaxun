import { useState } from "react";

export default function FileUpload({ onResult, onLoading, onError }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  // 文件大小格式化函数
  const formatFileSize = (size) => {
    if (size < 1024) return size + " B";
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB";
    return (size / (1024 * 1024)).toFixed(1) + " MB";
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    onLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      
      if (data.error) {
        onError(data.error);
      } else {
        onResult(data);
      }
    } catch (error) {
      console.error("上传失败:", error);
      onError("文件分析失败，请重试");
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