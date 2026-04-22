import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
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
   - `有效业绩总数` = 实际计入最终得分的业绩条数（受封顶影响）
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
  "合格业绩清单": [
    { "参考业绩": "项目简称", "通过原因": "满足具体档位规则" }
  ],
  "业绩剔除清单": [
    { "参考业绩": "项目简称", "剔除原因": "具体不符点" }
  ]
}
"""


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _normalize_name(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).strip()


def _parse_candidates_from_rag_context(rag_context: str) -> List[Dict[str, Any]]:
    """
    从 RAG 文本中提取候选项目名称与合同金额（万元）。
    """
    if not rag_context:
        return []

    chunks = re.split(r"【候选 #\d+】", rag_context)
    candidates: List[Dict[str, Any]] = []
    for chunk in chunks[1:]:
        name_m = re.search(r"项目名称：([^；\n]+)", chunk)
        amount_m = re.search(r"合同金额\(万元\)：([^；\n]+)", chunk)
        if not name_m:
            continue
        name = name_m.group(1).strip()
        amount = _to_float(amount_m.group(1).strip()) if amount_m else None
        candidates.append(
            {
                "name": name,
                "name_norm": _normalize_name(name),
                "amount_wan": amount,
            }
        )
    return candidates


def _parse_amount_slot_rule(slot_desc: str) -> Optional[Tuple[str, float, float, float]]:
    """
    解析类似“合同预算金额小于50万的项目每个加0.5分，最多2分”规则。
    返回 (op, threshold_wan, per_item_score, cap_score)。
    """
    if not slot_desc:
        return None

    desc = slot_desc.replace("万元", "万")
    threshold_m = re.search(r"(?:小于|低于|不超过|<=|≤)\s*(\d+(?:\.\d+)?)\s*万", desc)
    if threshold_m:
        op = "lt"
    else:
        threshold_m = re.search(r"(?:大于|高于|超过|>=|≥)\s*(\d+(?:\.\d+)?)\s*万", desc)
        op = "gt" if threshold_m else ""
    if not threshold_m:
        return None

    per_item_m = re.search(r"(?:每个|每项)[^\d]*(\d+(?:\.\d+)?)\s*分", desc)
    cap_m = re.search(r"(?:最多|最高|封顶)[^\d]*(\d+(?:\.\d+)?)\s*分", desc)
    if not per_item_m or not cap_m:
        return None

    threshold = float(threshold_m.group(1))
    per_item = float(per_item_m.group(1))
    cap = float(cap_m.group(1))
    return op, threshold, per_item, cap


def _count_scored_items_by_details(details: Any) -> int:
    """
    计算“实际计入最终得分”的业绩条数。
    对可解析“每个X分，最多Y分”的档位，按档位实际得分/每项分值反推计分条数；
    否则回退为 0，由上层兜底策略处理。
    """
    if not isinstance(details, list):
        return 0

    scored_items = 0
    for item in details:
        if not isinstance(item, dict):
            continue

        parsed = _parse_amount_slot_rule(str(item.get("得分档位", "")))
        if not parsed:
            continue

        per_item = parsed[2]
        if per_item <= 0:
            continue

        raw_score = _to_float(item.get("原始累计分值"))
        actual_score = _to_float(item.get("档位实际得分"))
        if raw_score is None or actual_score is None:
            continue

        raw_count = max(int(round(raw_score / per_item)), 0)
        actual_count = max(int(round(actual_score / per_item)), 0)
        scored_items += min(actual_count, raw_count)

    return max(scored_items, 0)


def _is_same_project_name(ref_name: str, cand_name: str) -> bool:
    ref_norm = _normalize_name(ref_name)
    cand_norm = _normalize_name(cand_name)
    if not ref_norm or not cand_norm:
        return False
    return ref_norm in cand_norm or cand_norm in ref_norm


def _build_amount_rule_lists(
    candidates: List[Dict[str, Any]],
    op: str,
    threshold: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    qualified: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    op_text = "小于" if op == "lt" else "大于"

    for c in candidates:
        name = str(c.get("name", "")).strip() or "未知项目"
        amount = c.get("amount_wan")
        if amount is None:
            excluded.append(
                {
                    "参考业绩": name,
                    "剔除原因": f"合同金额缺失，无法判定是否{op_text}{threshold}万元",
                }
            )
            continue

        amount = float(amount)
        ok = amount < threshold if op == "lt" else amount > threshold
        if ok:
            qualified.append(
                {
                    "参考业绩": name,
                    "通过原因": f"合同金额（{amount}万元）满足“{op_text}{threshold}万元”",
                }
            )
        else:
            excluded.append(
                {
                    "参考业绩": name,
                    "剔除原因": f"合同金额（{amount}万元）不满足“{op_text}{threshold}万元”",
                }
            )
    return qualified, excluded


def _apply_deterministic_amount_validation(
    result: Dict[str, Any],
    rag_context: str,
) -> Dict[str, Any]:
    """
    对金额档位执行确定性校验：
    - 基于 RAG 候选的合同金额重算档位分值；
    - 修正明显反向的剔除理由（如 12.8 万被写成“大于 50 万”）。
    """
    details = result.get("详细计算过程")
    if not isinstance(details, list) or not details:
        return result

    candidates = _parse_candidates_from_rag_context(rag_context)
    if not candidates:
        return result

    amount_rule: Optional[Tuple[str, float, float, float]] = None
    # 仅对可解析金额规则的档位做校验与重算。
    for item in details:
        if not isinstance(item, dict):
            continue
        slot_desc = str(item.get("得分档位", ""))
        parsed_rule = _parse_amount_slot_rule(slot_desc)
        if not parsed_rule:
            continue

        op, threshold, per_item, cap = parsed_rule
        if amount_rule is None:
            amount_rule = parsed_rule
        numeric_amounts = [c["amount_wan"] for c in candidates if c.get("amount_wan") is not None]
        if not numeric_amounts:
            continue

        if op == "lt":
            matched_count = sum(1 for amt in numeric_amounts if amt < threshold)
        else:
            matched_count = sum(1 for amt in numeric_amounts if amt > threshold)

        raw_score = matched_count * per_item
        actual_score = min(raw_score, cap)
        item["原始累计分值"] = round(raw_score, 4)
        item["档位实际得分"] = round(actual_score, 4)
        item["是否触碰封顶上限"] = "是" if raw_score >= cap and cap > 0 else "否"

        # 如果模型把金额比较方向判反，自动修正匹配说明。
        item["匹配说明"] = (
            f"确定性金额校验：按规则“{slot_desc}”在 RAG top-k 中识别到 "
            f"{matched_count} 个满足条件项目。"
        )

    # 构建“合格/剔除”两份清单，并确保仅来自 RAG top-k 候选。
    if amount_rule is not None:
        op, threshold, _, _ = amount_rule
        qualified_list, excluded_list = _build_amount_rule_lists(candidates, op, threshold)
        result["合格业绩清单"] = qualified_list
        result["业绩剔除清单"] = excluded_list
    else:
        # 无法解析金额规则时，至少保证清单只包含 top-k 中的项目。
        topk_names = [str(c.get("name", "")).strip() for c in candidates]
        old_exclusions = result.get("业绩剔除清单")
        filtered_exclusions: List[Dict[str, Any]] = []
        if isinstance(old_exclusions, list):
            for ex in old_exclusions:
                if not isinstance(ex, dict):
                    continue
                ref_name = str(ex.get("参考业绩") or ex.get("项目编号") or "").strip()
                if any(_is_same_project_name(ref_name, n) for n in topk_names):
                    filtered_exclusions.append(ex)
        result["业绩剔除清单"] = filtered_exclusions
        excluded_names = [
            str(ex.get("参考业绩") or ex.get("项目编号") or "").strip()
            for ex in filtered_exclusions
            if isinstance(ex, dict)
        ]
        qualified_fallback = []
        for n in topk_names:
            if not any(_is_same_project_name(n, exn) for exn in excluded_names):
                qualified_fallback.append({"参考业绩": n, "通过原因": "未在剔除清单中"})
        result["合格业绩清单"] = qualified_fallback

    # 重算总分与状态（只基于当前详细计算过程）。
    details_new = result.get("详细计算过程")
    if isinstance(details_new, list):
        total_score = 0.0
        for it in details_new:
            if isinstance(it, dict):
                total_score += _to_float(it.get("档位实际得分")) or 0.0
        summary = result.get("得分摘要")
        if not isinstance(summary, dict):
            summary = {}
            result["得分摘要"] = summary
        summary["最终总得分"] = round(total_score, 4)
        scored_count = _count_scored_items_by_details(details_new)
        qualified = result.get("合格业绩清单")
        excluded = result.get("业绩剔除清单")
        qualified_count = len(qualified) if isinstance(qualified, list) else 0
        excluded_count = len(excluded) if isinstance(excluded, list) else 0

        # 兜底规则：最终总分为 0 时，说明没有任何业绩被实际计分。
        if total_score <= 0:
            summary["有效业绩总数"] = 0
            # 某些不规则输出里会出现“总分为0但合格清单非空”，这里统一按无效业绩计入统计。
            summary["无效业绩总数"] = max(excluded_count, qualified_count)
        else:
            if scored_count > 0:
                summary["有效业绩总数"] = scored_count
            else:
                summary["有效业绩总数"] = qualified_count
            summary["无效业绩总数"] = excluded_count
        result["评审状态"] = "成功" if total_score > 0 else "失败"

    return result


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
        result = _apply_deterministic_amount_validation(result=result, rag_context=rag_context)
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