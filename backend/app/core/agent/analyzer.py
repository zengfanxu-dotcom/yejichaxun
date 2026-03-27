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

def analyze_tender(text: str, rag_context: str = "") -> dict:
    """
    调用智谱 LLM 分析招标文件，返回结构化结果
    """
    logger.info(f"开始分析文本，长度: {len(text)} 字符")
    if text:
        logger.info(f"文本前100字符: {text[:100]}...")
    else:
        logger.warning("输入文本为空")
    
    prompt = f"""
Role: 你是一名资深的政府采购招标文件评审专家，具备极强的逻辑核验与数据计算能力。
Task: 请根据用户提供的“招标文件业绩要求”，在预设的“公司业绩数据库”中检索符合条件的记录，并按照评分细则计算最终得分。
Execution Logic (执行逻辑):
有效性核验： 严格比对业绩时间（如2021年以来）和项目性质（如政府投资项目评审）。不符合条件的业绩直接排除。
分类匹配： 将有效业绩按“审定金额”划分至招标文件对应的得分区间（档位）。
分项计分： 计算每个档位的累计得分，注意： 必须遵守该档位的“最高得分（封顶分）限制”。
总分汇总： 将各档位最终得分相加，得出该项评审的总得分。
公司业绩库 - MVP测试用:
| ID | 年份 | 项目名称 | 审定金额 |
| :--- | :--- | :--- | :--- |
| 1 | 2022 | 政府投资项目评审预算业务A | 1500万元 |
| 2 | 2021 | 政府投资项目评审预算业务B | 2200万元 |
| 3 | 2023 | 政府投资项目评审预算业务C | 2800万元 |
| 4 | 2014 | 政府投资项目评审预算业务D | 2000万元 |
{{
  "评审状态": "成功/失败",
  "得分摘要": {{
    "最终总得分": 0.0,
    "有效业绩总数": 0,
    "无效业绩总数": 0
  }},
  "详细计算过程": [
    {{
      "得分档位": "档位描述",
      "匹配项目编号": [1, 2],
      "原始累计分值": 0.0,
      "档位实际得分": 0.0,
      "是否触碰封顶上限": "是/否"
    }}
  ],
  "业绩剔除清单": [
    {{ "项目编号": 4, "剔除原因": "原因说明" }}
  ]
}}

检索到的参考业绩（Top1）：
{rag_context}

文件内容：
{text}
"""
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