export default function ResultDisplay({ result }) {
  if (!result) return null; // 如果没有结果，则不渲染

  const { 评审状态, 得分摘要, 详细计算过程, 业绩剔除清单 } = result;

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>📊 评审结果</h2>

      {/* 评审状态 */}
      <div style={styles.section}>
        <span style={styles.label}>评审状态：</span>
        <span
          style={{
            ...styles.status,
            color: 评审状态 === "成功" ? "green" : "red",
          }}
        >
          {评审状态}
        </span>
      </div>

      {/* 得分摘要 */}
      {得分摘要 && (
        <div style={styles.section}>
          <span style={styles.label}>得分摘要：</span>
          <ul>
            <li>最终总得分: {得分摘要.最终总得分}</li>
            <li>有效业绩总数: {得分摘要.有效业绩总数}</li>
            <li>无效业绩总数: {得分摘要.无效业绩总数}</li>
          </ul>
        </div>
      )}

      {/* 详细计算过程 */}
      {详细计算过程 && 详细计算过程.length > 0 && (
        <div style={styles.section}>
          <span style={styles.label}>详细计算过程：</span>
          <ul>
            {详细计算过程.map((item, index) => (
              <li key={index}>
                <p>得分档位: {item.得分档位}</p>
                <p>匹配项目编号: {item.匹配项目编号.join(', ')}</p>
                <p>原始累计分值: {item.原始累计分值}</p>
                <p>档位实际得分: {item.档位实际得分}</p>
                <p>是否触碰封顶上限: {item.是否触碰封顶上限}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 业绩剔除清单 */}
      {业绩剔除清单 && 业绩剔除清单.length > 0 && (
        <div style={styles.section}>
          <span style={styles.label}>业绩剔除清单：</span>
          <ul>
            {业绩剔除清单.map((item, index) => (
              <li key={index}>
                <p>项目编号: {item.项目编号}</p>
                <p>剔除原因: {item.剔除原因}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

const styles = {
  card: {
    marginTop: "20px",
    padding: "20px",
    borderRadius: "10px",
    background: "#f9f9f9",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    maxWidth: "600px",
  },
  title: {
    marginBottom: "15px",
    borderBottom: "2px solid #007bff",
    paddingBottom: "10px",
  },
  section: {
    marginBottom: "12px",
  },
  label: {
    fontWeight: "bold",
    marginRight: "8px",
  },
  status: {
    fontWeight: "bold",
    fontSize: "16px",
  },
  reason: {
    marginTop: "5px",
    lineHeight: "1.5",
  },
};