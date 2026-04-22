import logging
import re
import os
import threading
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from backend.app.core.tools.data_preprocessor import process_project_data_to_documents
from backend.app.core.tools.rag_system import RAGSystem

logger = logging.getLogger(__name__)

_rag_system = RAGSystem()
_rag_initialized = False
_rag_lock = threading.RLock()
_active_slot: Optional[str] = None

SLOT_A = "A"
SLOT_B = "B"
SLOT_NAMES = (SLOT_A, SLOT_B)

# 默认：向量召回 K、送入 LLM 条数、检索 query 最大字符数
RAG_RETRIEVE_K = 8
RAG_LLM_MAX_DOCS = 6
RAG_QUERY_MAX_LEN = 1500


def get_rag_system() -> RAGSystem:
    return _rag_system


def _chroma_root_dir() -> str:
    """
    使用仓库根目录的绝对路径，避免 uvicorn/reload 时工作目录变化导致
    persist 目录相对路径失效，从而出现 collection 不存在。
    """
    tools_dir = os.path.dirname(__file__)  # .../backend/app/core/tools
    # tools -> core -> app -> backend -> repo root
    repo_root = os.path.abspath(os.path.join(tools_dir, "../../../../"))
    return os.path.join(repo_root, "chroma_db")


CHROMA_ROOT_DIR = _chroma_root_dir()
CHROMA_SLOTS_DIR = os.path.join(CHROMA_ROOT_DIR, "slots")
ACTIVE_SLOT_FILE = os.path.join(CHROMA_ROOT_DIR, "active_slot.txt")


def _slot_persist_dir(slot: str) -> str:
    return os.path.join(CHROMA_SLOTS_DIR, slot)


def _read_active_slot() -> Optional[str]:
    if not os.path.exists(ACTIVE_SLOT_FILE):
        return None
    try:
        with open(ACTIVE_SLOT_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip().upper()
            return value if value in SLOT_NAMES else None
    except Exception:
        return None


def _write_active_slot(slot: str) -> None:
    os.makedirs(CHROMA_ROOT_DIR, exist_ok=True)
    tmp_path = ACTIVE_SLOT_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(slot)
    os.replace(tmp_path, ACTIVE_SLOT_FILE)


def _other_slot(slot: Optional[str]) -> str:
    if slot == SLOT_A:
        return SLOT_B
    return SLOT_A


def get_active_slot() -> Optional[str]:
    with _rag_lock:
        return _active_slot or _read_active_slot()


def _load_slot_if_available(slot: str) -> bool:
    persist_dir = _slot_persist_dir(slot)
    if not os.path.exists(persist_dir):
        return False
    try:
        _rag_system.load_vector_store(persist_directory=persist_dir)
        return True
    except Exception as e:
        logger.warning("RAG槽位加载失败 slot=%s: %s", slot, e)
        return False


def ensure_rag_initialized() -> None:
    global _rag_initialized, _active_slot
    with _rag_lock:
        if _rag_initialized and _rag_system.vector_store is not None:
            return

        preferred_slot = _read_active_slot()
        if preferred_slot and _load_slot_if_available(preferred_slot):
            _rag_initialized = True
            _active_slot = preferred_slot
            logger.info("RAG向量库已加载（active_slot=%s）", preferred_slot)
            return

        for slot in SLOT_NAMES:
            if _load_slot_if_available(slot):
                _rag_initialized = True
                _active_slot = slot
                _write_active_slot(slot)
                logger.warning("RAG active slot 恢复为 %s", slot)
                return

        # 向后兼容：旧版单目录结构（chroma_db 根目录）。
        try:
            if os.path.exists(CHROMA_ROOT_DIR):
                _rag_system.load_vector_store(persist_directory=CHROMA_ROOT_DIR)
                _rag_initialized = True
                _active_slot = None
                logger.info("RAG向量库已从旧版目录加载（legacy mode）")
                return
        except Exception as e:
            logger.warning("RAG向量库持久化加载失败，将回退全量构建: %s", e)

        project_docs = process_project_data_to_documents()
        if not project_docs:
            raise RuntimeError("RAG重建失败：未生成任何 documents")

        os.makedirs(CHROMA_SLOTS_DIR, exist_ok=True)
        target_slot = SLOT_A
        _rag_system.initialize_vector_store(
            project_docs,
            persist_directory=_slot_persist_dir(target_slot),
            wipe_persist_directory=True,
        )
        _write_active_slot(target_slot)
        _active_slot = target_slot
        _rag_initialized = True
        logger.info("RAG向量库初始化完成（active_slot=%s）", target_slot)


def rebuild_rag_index() -> int:
    """
    强制清理并全量重建向量库。

    适用于本地持久化目录损坏、版本切换导致不兼容等场景。
    """
    global _rag_initialized, _rag_system, _active_slot
    project_docs = process_project_data_to_documents()
    if not project_docs:
        raise RuntimeError("RAG重建失败：未生成任何 documents")

    with _rag_lock:
        current_slot = _active_slot or _read_active_slot()
        target_slot = _other_slot(current_slot)

    os.makedirs(CHROMA_SLOTS_DIR, exist_ok=True)
    target_dir = _slot_persist_dir(target_slot)

    # 先在备用槽位构建，在线槽位继续服务；构建成功后再做原子切换。
    builder = RAGSystem()
    builder.initialize_vector_store(
        project_docs,
        persist_directory=target_dir,
        wipe_persist_directory=True,
    )
    n = builder.get_document_count()
    if n <= 0:
        raise RuntimeError("RAG重建失败：新槽位文档数为 0")

    with _rag_lock:
        old_slot = _active_slot
        _rag_system = builder
        _rag_initialized = True
        _active_slot = target_slot
        _write_active_slot(target_slot)

    logger.info("RAG 双槽位切换完成: %s -> %s, 文档数 %s", old_slot or "legacy", target_slot, n)
    return n


def build_rag_query(tender_text: str, max_len: int = RAG_QUERY_MAX_LEN) -> str:
    """检索用 query：截取招标正文前 max_len 字（与 upload 侧全文分析分离）。"""
    if not tender_text:
        return ""
    t = tender_text.strip()
    if len(t) <= max_len:
        return t
    return t[:max_len]


def extract_min_contract_wan(tender_text: str) -> Optional[float]:
    """
    从招标正文中启发式解析「合同金额下限（万元）」，用于候选排序（非严格法律依据）。
    解析失败返回 None，不做金额硬过滤。
    """
    if not tender_text or not tender_text.strip():
        return None
    text = tender_text
    candidates: List[float] = []
    # 针对严格“> / 大于 / 超过 / 高于”的下限：由于后续判定使用 `amt >= min_wan`，
    # 给严格比较添加极小 epsilon，避免等于边界时被误判为达标。
    epsilon = 1e-6

    # 非严格下限：>= / ≥ / 不低于 / 至少 / 及以上等
    patterns_ge = [
        r"(?:≥|>=|≧|不少于|不低于|达到|应达到|须达到|至少)\s*(\d+(?:\.\d+)?)\s*万(?:元)?",
        r"(\d+(?:\.\d+)?)\s*万元\s*(?:及以?上|人民币)?",
        r"(\d+(?:\.\d+)?)\s*万\s*元\s*(?:及以?上|人民币)?",
    ]

    # 严格比较下限：> / 大于(非等于) / 超过 / 高于
    patterns_gt = [
        r"(?:大于(?!等于)|超过|高于|>)\s*(\d+(?:\.\d+)?)\s*万(?:元)?",
    ]

    for pat in patterns_ge:
        for m in re.finditer(pat, text):
            try:
                candidates.append(float(m.group(1)))
            except ValueError:
                continue

    for pat in patterns_gt:
        for m in re.finditer(pat, text):
            try:
                candidates.append(float(m.group(1)) + epsilon)
            except ValueError:
                continue

    if not candidates:
        return None

    # 保守取最大解析值作为「常提到的门槛」下限代理（复杂分档表需后续专门解析）
    return max(candidates)


def _rank_candidates(
    scored: List[Tuple[Document, float]],
    min_contract_wan: Optional[float],
) -> List[Tuple[Document, float, bool, int]]:
    """
    对 (doc, distance) 列表重排：若解析到金额门槛，则 metadata 合同额达标者优先，同组内距离升序。
    original_rank 为向量召回名次（1-based）。
    """
    enriched: List[Tuple[Document, float, bool, int]] = []
    for i, (doc, dist) in enumerate(scored, start=1):
        amt = RAGSystem.contract_amount_wan_from_doc(doc)
        if min_contract_wan is None:
            eligible = True
        elif amt is None:
            eligible = True
        else:
            eligible = amt >= min_contract_wan
        enriched.append((doc, dist, eligible, i))

    enriched.sort(key=lambda x: (not x[2], x[1]))
    return enriched


def _format_multi_doc_prompt(
    ranked: List[Tuple[Document, float, bool, int]],
    min_contract_wan: Optional[float],
    max_docs: int,
) -> str:
    if not ranked:
        return "无可用检索结果"

    lines: List[str] = []
    if min_contract_wan is not None:
        lines.append(
            f"说明：从招标文件中启发式解析的合同金额下限约为 **{min_contract_wan} 万元**（仅用于候选排序，以原文为准）。"
        )
    else:
        lines.append(
            "说明：未能从招标文件中解析出明确的合同金额下限，候选仅按向量相似度排序。"
        )
    lines.append(
        f"以下至多 **{max_docs}** 条候选，已按「合同额达标（若能解析且 metadata 有金额）优先 + 向量距离升序」重排；请在原文中逐项核验。"
    )
    lines.append("")

    for idx, (doc, dist, eligible, vec_rank) in enumerate(ranked[:max_docs], start=1):
        amt = RAGSystem.contract_amount_wan_from_doc(doc)
        amt_s = f"{amt}" if amt is not None else "（metadata 无金额）"
        if min_contract_wan is not None and amt is not None and not eligible:
            flag = f"否；合同额 {amt_s} 万元未达解析门槛 {min_contract_wan} 万元（仍列出供核对）"
        elif min_contract_wan is not None and amt is not None and eligible:
            flag = f"是（合同额 {amt_s} 万元）"
        else:
            flag = "未判定（门槛或业绩金额缺失）"
        body = RAGSystem.format_doc_for_prompt(doc)
        lines.append(
            f"【候选 #{idx}】向量召回名次：{vec_rank}；距离：{dist:.4f}；规则预判达标：{flag}\n{body}\n"
        )

    return "\n".join(lines).strip()


def query_topk_context(
    tender_text: str,
    retrieve_k: int = RAG_RETRIEVE_K,
    llm_max_docs: int = RAG_LLM_MAX_DOCS,
    query_max_len: int = RAG_QUERY_MAX_LEN,
) -> str:
    """
    用招标正文构造 query（截断）→ 向量 Top-K → 可选金额门槛重排 → 取前 llm_max_docs 条拼进 prompt。
    """
    with _rag_lock:
        ensure_rag_initialized()
        query = build_rag_query(tender_text, max_len=query_max_len)
        if not query.strip():
            return "无可用检索结果"

        scored = _rag_system.similarity_search_with_score(query=query, k=retrieve_k)
        min_wan = extract_min_contract_wan(tender_text)
        ranked = _rank_candidates(scored, min_wan)
        return _format_multi_doc_prompt(ranked, min_wan, max_docs=llm_max_docs)


def query_top1_context(query: str) -> str:
    """调试/兼容：仅取向量最近 1 条。"""
    with _rag_lock:
        ensure_rag_initialized()
        top1_doc: Optional[Document] = _rag_system.retrieve_top1(query=query)
        return _rag_system.format_doc_for_prompt(top1_doc)
