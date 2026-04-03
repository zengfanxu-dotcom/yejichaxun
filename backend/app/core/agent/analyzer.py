import json
import logging
from backend.app.core.agent.zhipu_llm import ZhipuLLM  # 你之前封装的智谱 LLM

# 配置日志
logger = logging.getLogger(__name__)

def _extract_json_from_markdown(text: str) -> str:
    """
    从可能包含Markdown代码块的字符串中提取JSON内容。
    """
    # 查找以 ```json 开头和 ``` 结尾的模式
    start_tag = "```json"
    end_tag = "```"
    
    start_index = text.find(start_tag)
    if start_index == -1:
        # 如果没有找到开始标签，尝试直接返回原始文本，或者抛出错误，具体取决于预期行为
        return text 

    end_index = text.rfind(end_tag)
    if end_index == -1 or end_index <= start_index:
        # 如果没有找到结束标签，或者结束标签在开始标签之前，也尝试返回原始文本
        return text

    # 提取JSON内容
    json_content = text[start_index + len(start_tag):end_index].strip()
    return json_content

# 初始化 LLM 实例（全局复用）
llm = ZhipuLLM()

# 静态指令（非 f-string，避免 JSON 示例中的花括号转义）
TENDER_ANALYSIS_INSTRUCTIONS = """
## 角色
政采招标评审专家。仅依据上下文「参考业绩」与「评分要求」（=招标文件原文中的评分细则）评分，严禁虚构。

## 核心逻辑（硬约束）
1. **有效性判定**：严格匹配时间/性质/金额。不符则剔除，得分必为 0。
2. **状态绑定**：
   - `评审状态: 成功` ⇔ `最终总得分 > 0`
   - `评审状态: 失败` ⇔ `最终总得分 == 0`（含：无业绩、全剔除、规则不明）
3. **分值勾稽**（受封顶限制）：
   - `最终总得分` = ∑ 各档 `档位实际得分`
   - `有效业绩总数` + `无效业绩总数` = 检索到的总业绩条数（Max: 4）
   - **互斥原则**：出现在「业绩剔除清单」的项目，其得分必为 0，且不得计入 `有效业绩总数`

## 输出格式
只输出 JSON，禁止解释。示例仅为结构参考，禁止照抄数值。
{
  "评审状态": "成功/失败",
  "得分摘要": {
    "最终总得分": 0.0,
    "有效业绩总数": 0,
    "无效业绩总数": 0
  },
  "详细计算过程": [
    {
      "得分档位": "原文描述",
      "匹配说明": "简述匹配/剔除理由",
      "档位实际得分": 0.0,
      "是否触碰封顶上限": "是/否",
      "原始累计分值": 0.0
    }
  ],
  "业绩剔除清单": [
    { "参考业绩": "项目简称", "剔除原因": "具体不符点" }
  ]
}
"""


def _build_tender_analysis_prompt(rag_context: str, tender_text: str) -> str:
    rag_body = rag_context.strip() if rag_context else "（未提供检索结果）"
    sections = [
        TENDER_ANALYSIS_INSTRUCTIONS.strip(),
        "## 检索参考业绩（至多4条，向量召回后排序）\n\n" + rag_body,
        "## 招标文件原文\n\n" + (tender_text or ""),
    ]
    return "\n\n---\n\n".join(sections)


def analyze_tender(text: str, rag_context: str = "") -> dict:
    """
    调用智谱 LLM 分析招标文件，返回结构化结果
    """
    logger.info(f"开始分析文本，长度: {len(text)} 字符")
    if text:
        logger.info(f"文本前100字符: {text[:100]}...")
    else:
        logger.warning("输入文本为空")

    prompt = _build_tender_analysis_prompt(rag_context=rag_context, tender_text=text)
    logger.info(f"生成提示词，长度: {len(prompt)} 字符")
    
    # 调用 LLM 获取文本结果
    try:
        result_text = llm.invoke(prompt)
        logger.info(f"LLM返回结果，长度: {len(result_text)} 字符")
        logger.info(f"LLM返回结果前100字符: {result_text[:100]}...")
    except Exception as e:
        logger.error(f"LLM调用失败: {str(e)}", exc_info=True)
        raise Exception(f"LLM调用失败: {str(e)}")

    clean_json_text = _extract_json_from_markdown(result_text)
    logger.info(f"提取的纯净JSON文本长度: {len(clean_json_text)} 字符")
    logger.info(f"提取的纯净JSON文本前100字符: {clean_json_text[:100]}...")
    
    # 解析 JSON
    try:
        result = json.loads(clean_json_text)
        logger.info(f"JSON解析成功: {result}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        logger.error(f"无效的JSON内容: {clean_json_text[:200]}...")
        # 出错时返回空结构，避免整个接口挂掉
        result = {
            "关键业绩要求": [],
            "金额要求": "",
            "符合条件": False
        }
        logger.info(f"返回默认结果: {result}")
        return result
    except Exception as e:
        logger.error(f"分析过程中发生其他错误: {str(e)}", exc_info=True)
        raise Exception(f"分析过程中发生错误: {str(e)}")