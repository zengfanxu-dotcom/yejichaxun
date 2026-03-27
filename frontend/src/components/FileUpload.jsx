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
    <div>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => {
          const selectedFile = e.target.files[0];
          setFile(selectedFile);
        }}
      />

      {file && (
        <div style={styles.fileInfo}>
          <p>📄 文件名：{file.name}</p>
          <p>📦 文件大小：{formatFileSize(file.size)}</p>
        </div>
      )}

      <button onClick={handleUpload} disabled={loading}>
        {loading ? "分析中..." : "上传并分析"}
      </button>
    </div>
  );
}

const styles = {
  fileInfo: {
    marginTop: "10px",
    padding: "10px",
    background: "#f5f5f5",
    borderRadius: "6px",
  },
};