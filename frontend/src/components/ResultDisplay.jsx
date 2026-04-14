function formatMatchingField(item) {
  const ids = item?.匹配项目编号;
  if (Array.isArray(ids) && ids.length > 0) {
    return ids.join(", ");
  }
  if (item?.匹配说明 != null && item.匹配说明 !== "") {
    return String(item.匹配说明);
  }
  return "—";
}

export default function ResultDisplay({ result }) {
  if (!result) return null; // 如果没有结果，则不渲染

  const { 评审状态, 得分摘要, 详细计算过程, 合格业绩清单, 业绩剔除清单 } = result;

  return (
    <section className="result-card">
      <h2 className="result-title">评审结果</h2>

      {/* 评审状态 */}
      <div className="result-section">
        <span className="result-label">评审状态：</span>
        <span className={`result-status ${评审状态 === "成功" ? "success" : "fail"}`}>
          {评审状态}
        </span>
      </div>

      {/* 得分摘要 */}
      {得分摘要 && (
        <div className="result-section">
          <span className="result-label">得分摘要：</span>
          <ul className="result-list">
            <li>最终总得分: {得分摘要.最终总得分}</li>
            <li>有效业绩总数: {得分摘要.有效业绩总数}</li>
            <li>无效业绩总数: {得分摘要.无效业绩总数}</li>
          </ul>
        </div>
      )}

      {/* 详细计算过程 */}
      {详细计算过程 && 详细计算过程.length > 0 && (
        <div className="result-section">
          <span className="result-label">详细计算过程：</span>
          <ul className="result-list process-list">
            {详细计算过程.map((item, index) => (
              <li key={index} className="result-item">
                <p>得分档位: {item.得分档位}</p>
                <p>匹配说明: {formatMatchingField(item)}</p>
                <p>原始累计分值: {item.原始累计分值}</p>
                <p>档位实际得分: {item.档位实际得分}</p>
                <p>是否触碰封顶上限: {item.是否触碰封顶上限}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 合格业绩清单 */}
      {合格业绩清单 && 合格业绩清单.length > 0 && (
        <div className="result-section">
          <span className="result-label">合格业绩清单：</span>
          <ul className="result-list process-list">
            {合格业绩清单.map((item, index) => (
              <li key={index} className="result-item">
                <p>
                  参考业绩:{" "}
                  {item.参考业绩 != null && item.参考业绩 !== ""
                    ? item.参考业绩
                    : item.项目编号 != null
                      ? item.项目编号
                      : "—"}
                </p>
                <p>通过原因: {item.通过原因 ?? "—"}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 业绩剔除清单 */}
      {业绩剔除清单 && 业绩剔除清单.length > 0 && (
        <div className="result-section">
          <span className="result-label">业绩剔除清单：</span>
          <ul className="result-list process-list">
            {业绩剔除清单.map((item, index) => (
              <li key={index} className="result-item">
                <p>
                  参考业绩:{" "}
                  {item.参考业绩 != null && item.参考业绩 !== ""
                    ? item.参考业绩
                    : item.项目编号 != null
                      ? item.项目编号
                      : "—"}
                </p>
                <p>剔除原因: {item.剔除原因 ?? "—"}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}