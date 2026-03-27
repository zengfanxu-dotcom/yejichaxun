import pandas as pd
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
import logging
import os
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _normalize_column_name(col: str) -> str:
    """标准化列名：去空格 / 中英文括号统一 / 小写"""
    if not col:
        return col
    col = str(col).strip()
    col = re.sub(r"\s+", "", col)
    col = col.replace("（", "(").replace("）", ")")
    return col.lower()


def _clean_empty(v):
    """统一空值"""
    if v in ["", "nan", None]:
        return None
    return v


def _extract_year(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return int(value.year)

    s = str(value)
    m = re.search(r"(19\d{2}|20\d{2})", s)
    if m:
        return int(m.group(1))

    m2 = re.match(r"^\s*(\d{4})", s)
    if m2:
        return int(m2.group(1))

    return None


def _to_float_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None
    s = re.sub(r"[^\d.]+", "", s)
    try:
        return float(s) if s else None
    except Exception:
        return None


def process_project_data_to_documents(file_path: str = None) -> List[Document]:
    if file_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(base_dir, '..', '..', 'database', 'data')
        preferred = '业绩JL.xlsx'
        preferred_path = os.path.join(data_dir, preferred)
        if os.path.exists(preferred_path):
            file_path = preferred_path
        else:
            xls_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".xls")]
            xlsx_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".xlsx")]
            candidates = xls_files or xlsx_files
            if not candidates:
                raise FileNotFoundError(f"No .xls/.xlsx file found in {data_dir}")
            file_path = os.path.join(data_dir, candidates[0])

    logger.info(f"正在从文件 {file_path} 加载数据...")

    try:
        df = pd.read_excel(file_path)
        logger.info(f"成功读取Excel文件，共 {len(df)} 行数据")

        # ✅ 列名标准化（关键优化）
        df.columns = [_normalize_column_name(c) for c in df.columns]
        logger.info(f"规范化后的列名: {df.columns.tolist()}")

    except Exception as e:
        logger.error(f"读取Excel文件失败: {e}")
        logger.info("使用模拟数据代替...")
        data = {
            " 项目名称 ": ["某跨海大桥一期工程", "高新区地下管网改造", "总部办公大楼建设", None], # 模拟带有前后空格的列名，以及 None 值
            " 合同 预算金额（万元） ": ["15000.5", None, "3200.00", "1.2万"], # 模拟带有内部空格的列名，以及 None 值和“万”单位
            " 年份 ": ["2022", "2023 ", None, "2020"], # 模拟带有前后空格的列名，以及 None 值
            "项目类型": ["桥梁工程", "水利工程 ", None, "工业园"], # 模拟 None 值
            " 项目经理 ": [None, "李四", "王五", "赵六"], # 模拟 None 值
            " 竣工时间 ": ["2022-12-31", None, "2021", "2020-01-01"], # 模拟 None 值
            " 投资额（万元） ": [100000.0, 80000, 50000, None], # 模拟 None 值
            "委托单位": ["A公司", "B公司", "C公司", None], # 模拟 None 值
        }
        df = pd.DataFrame(data)

    logger.info("正在清洗数据并规范化字段...")
    columns = df.columns.tolist()
    logger.info(f"检测到的列名: {columns}")

    if len(columns) >= 12:
        c_signed_contract_time = columns[0]
        c_project_name = columns[1]
        c_manager = columns[2]
        c_investment_amount = columns[3]
        c_contract_budget_amount = columns[4]
        c_scale = columns[5]
        c_client_unit = columns[6]
        c_specialty = columns[7]
        c_completion_time = columns[8]
        c_contract_file_style = columns[9]
        c_completion_acceptance = columns[10]
        c_project_address = columns[11]

        logger.info("检测到列数>=12，启用固定列序号映射（不依赖列名编码）。")

        df["__signed_contract_time__"] = df[c_signed_contract_time].astype(str).replace("nan", "").str.strip()
        df["__project_name_full__"] = df[c_project_name].astype(str).replace("nan", "").str.strip()
        df["__manager_full__"] = df[c_manager].astype(str).replace("nan", "").str.strip()

        df["__investment_amount__"] = df[c_investment_amount].apply(_to_float_amount)
        df["__contract_budget_amount__"] = df[c_contract_budget_amount].apply(_to_float_amount)

        df["__scale__"] = df[c_scale].astype(str).replace("nan", "").str.strip()
        df["__client_unit__"] = df[c_client_unit].astype(str).replace("nan", "").str.strip()
        df["__specialty__"] = df[c_specialty].astype(str).replace("nan", "").str.strip()
        df["__completion_time__"] = df[c_completion_time].astype(str).replace("nan", "").str.strip()
        df["__contract_file_style__"] = df[c_contract_file_style].astype(str).replace("nan", "").str.strip()
        df["__completion_acceptance__"] = df[c_completion_acceptance].astype(str).replace("nan", "").str.strip()
        df["__project_address__"] = df[c_project_address].astype(str).replace("nan", "").str.strip()

        # ✅ 核心字段（统一）
        df["__project_name__"] = df["__project_name_full__"].replace("", None)
        df["__manager__"] = df["__manager_full__"].replace("", None)
        df["__type__"] = df["__specialty__"].replace("", None)

        # ✅ 金额拆分（关键优化）
        df["__contract_amount__"] = df["__contract_budget_amount__"]
        df["__investment_amount_clean__"] = df["__investment_amount__"]

        # ✅ 年份修复（关键）
        df["__year__"] = df[c_signed_contract_time].apply(_extract_year)

        # ✅ 异常检测
        def _check_amount_anomaly(row):
            contract = row.get("__contract_amount__")
            invest = row.get("__investment_amount_clean__")
            if contract and invest and contract > invest * 10:
                logger.warning(f"⚠️ 金额异常：合同金额({contract}) >> 投资额({invest})")

        df.apply(_check_amount_anomaly, axis=1)

    else:
        logger.warning("列数不足12，启用降级处理")
        return []

    logger.info("正在构建 Documents...\n")
    documents = []

    for _, row in df.iterrows():
        metadata = {
            # ✅ 标准字段（干净schema）
            "project_name": row.get("__project_name__", None),
            "year": row.get("__year__", None),
            "contract_amount": row.get("__contract_amount__", None),
            "investment_amount": row.get("__investment_amount_clean__", None),
            "type": row.get("__type__", None),
            "manager": row.get("__manager__", None),

            # ✅ 兼容旧系统
            "amount": row.get("__contract_amount__", None),

            # 原始字段（用于展示）
            "签订合同时间": row.get("__signed_contract_time__", None),
            "项目名称": row.get("__project_name_full__", None),
            "总监": row.get("__manager_full__", None),
            "规模": row.get("__scale__", None),
            "委托单位": row.get("__client_unit__", None),
            "专业": row.get("__specialty__", None),
            "竣工时间": row.get("__completion_time__", None),
            "合同文件样式": row.get("__contract_file_style__", None),
            "竣工验收单": row.get("__completion_acceptance__", None),
            "项目地址": row.get("__project_address__", None),
        }

        # 清洗空值
        metadata = {k: _clean_empty(v) for k, v in metadata.items()}

        page_content = (
            f"项目名称：{metadata.get('项目名称')}；总监：{metadata.get('总监')}；"
            f"签订合同时间：{metadata.get('签订合同时间')}；竣工时间：{metadata.get('竣工时间')}；"
            f"投资额（万元）：{metadata.get('investment_amount')}；合同金额（万元）：{metadata.get('contract_amount')}；"
            f"规模：{metadata.get('规模')}；委托单位：{metadata.get('委托单位')}；专业：{metadata.get('专业')}；"
            f"合同文件样式：{metadata.get('合同文件样式')}；竣工验收单：{metadata.get('竣工验收单')}；项目地址：{metadata.get('项目地址')}；"
            f"合同总金额（用于评分匹配）：{metadata.get('contract_amount')}万元。"
        )

        documents.append(Document(page_content=page_content, metadata=metadata))

    return documents