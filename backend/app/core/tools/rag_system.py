import gc
import logging
import os
import re
import time
from typing import List, Optional, Tuple

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _chroma_persist_settings():
    """与 PersistentClient.reset 一致，避免同一路径出现 different settings 报错。"""
    from chromadb.config import Settings

    return Settings(allow_reset=True, is_persistent=True)


class RAGSystem:
    """
    最小RAG实现（可扩展）：
    query -> embedding -> Chroma -> top-k -> 上层拼接 prompt（由 rag_runtime 做截断与排序说明）
    """

    def __init__(
        self,
        embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        # multilingual 模型与中文查询/中文业绩描述更匹配；384 维与旧版 all-MiniLM-L6-v2 一致
        self.embedding_model = HuggingFaceEmbeddings(model_name=embedding_model_name)
        self.vector_store: Optional[Chroma] = None

    def _release_vector_store(self) -> None:
        """释放 Chroma 客户端，避免 Windows 上占用 chroma_db 文件导致无法删除目录。"""
        vs = self.vector_store
        self.vector_store = None
        if vs is None:
            return
        try:
            vs.delete_collection()
        except Exception as e:
            logger.warning("释放 Chroma 集合时: %s", e)
        del vs
        gc.collect()
        time.sleep(0.08)

    def _wipe_persist_directory_via_chroma(self, persist_directory: str) -> None:
        """
        在「已释放 LangChain Chroma 实例」之后，用官方 reset 清空持久化库，
        避免 Windows 下 rmtree 与 mmap 文件句柄冲突（WinError 32）。
        """
        try:
            import chromadb

            settings = _chroma_persist_settings()
            client = chromadb.PersistentClient(path=persist_directory, settings=settings)
            try:
                client.reset()
            finally:
                del client
                gc.collect()
        except Exception as e:
            logger.warning("Chroma reset 失败（若目录不存在可忽略）: %s", e)

    def load_vector_store(self, persist_directory: str) -> None:
        """
        只加载已存在的持久化向量库。

        注意：此方法不进行 reset/wipe，避免与并发查询/重建产生集合缺失窗口。
        """
        # Chroma 的 LangChain 默认 collection_name 是 'langchain'
        self.vector_store = Chroma(
            collection_name="langchain",
            embedding_function=self.embedding_model,
            persist_directory=persist_directory,
            client_settings=_chroma_persist_settings(),
        )

        # 触发一次内部计数校验，确保 collection 确实存在
        #（如果不存在，通常会在内部访问 collection 时抛异常）
        self.vector_store._collection.count()

    def get_document_count(self) -> int:
        """尽量读取底层 collection 的文档数量，失败则返回 0。"""
        if not self.vector_store:
            return 0
        try:
            return int(self.vector_store._collection.count())
        except Exception:
            return 0

    def initialize_vector_store(
        self,
        documents: List[Document],
        persist_directory: Optional[str] = None,
        wipe_persist_directory: bool = False,
    ):
        if not documents:
            logger.warning("初始化向量库时文档为空，跳过。")
            return

        logger.info("正在初始化向量存储...")
        if persist_directory:
            os.makedirs(persist_directory, exist_ok=True)
            if wipe_persist_directory:
                # 仅在“必须全量重建/修复异常”场景才 wipe，避免无意义的清空造成集合缺失。
                # 释放 LangChain 持有的实例，再用原生 client reset（避免 Windows mmap/句柄冲突）
                self._release_vector_store()
                self._wipe_persist_directory_via_chroma(persist_directory)
                time.sleep(0.05)
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                persist_directory=persist_directory,
                client_settings=_chroma_persist_settings(),
            )
        else:
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_model,
            )
        logger.info("向量存储初始化完成，共 %s 条文档", len(documents))

    def add_documents(self, documents: List[Document]):
        if not documents:
            return
        if not self.vector_store:
            self.initialize_vector_store(documents)
            return
        self.vector_store.add_documents(documents)

    def similarity_search(self, query: str, k: int = 1) -> List[Document]:
        if not self.vector_store:
            return []
        return self.vector_store.similarity_search(query, k=k)

    def similarity_search_with_score(self, query: str, k: int = 8) -> List[Tuple[Document, float]]:
        """
        返回 (文档, 距离分)。Chroma 余弦距离通常「越小越相似」。
        """
        if not self.vector_store:
            return []
        return self.vector_store.similarity_search_with_score(query, k=k)

    def retrieve_top1(self, query: str) -> Optional[Document]:
        docs = self.similarity_search(query=query, k=1)
        return docs[0] if docs else None

    @staticmethod
    def contract_amount_wan_from_doc(doc: Optional[Document]) -> Optional[float]:
        """从 metadata 读取合同金额（万元），无法解析则 None。"""
        if not doc or not doc.metadata:
            return None
        md = doc.metadata
        for key in ("contract_amount", "amount"):
            v = md.get(key)
            if v is None:
                continue
            if isinstance(v, (int, float)):
                if isinstance(v, float) and v != v:  # NaN
                    continue
                return float(v)
            s = str(v).strip()
            if not s or s.lower() == "nan":
                continue
            s = re.sub(r"[^\d.]+", "", s)
            if not s:
                continue
            try:
                return float(s)
            except ValueError:
                continue
        return None

    @staticmethod
    def _first_meta(md: dict, *keys: str) -> str:
        """取 metadata 中第一个有意义（非空）的值，与 data_preprocessor 写入键对齐。"""
        for k in keys:
            v = md.get(k)
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            return str(v).strip()
        return ""

    @staticmethod
    def format_doc_for_prompt(doc: Optional[Document]) -> str:
        if not doc:
            return "无可用检索结果"
        md = doc.metadata or {}
        signed = RAGSystem._first_meta(md, "签订合同时间")
        year = RAGSystem._first_meta(md, "year")
        pname = RAGSystem._first_meta(md, "项目名称", "project_name")
        director = RAGSystem._first_meta(md, "总监", "manager")
        contract_amt = RAGSystem._first_meta(md, "contract_amount", "amount")
        invest_amt = RAGSystem._first_meta(md, "investment_amount")
        scale = RAGSystem._first_meta(md, "规模")
        client = RAGSystem._first_meta(md, "委托单位")
        specialty = RAGSystem._first_meta(md, "专业")
        typ = RAGSystem._first_meta(md, "type")
        if specialty and typ and specialty != typ:
            pro_seg = f"专业：{specialty}；类型：{typ}"
        else:
            pro_seg = f"专业/类型：{specialty or typ}"
        completion = RAGSystem._first_meta(md, "竣工时间")
        file_style = RAGSystem._first_meta(md, "合同文件样式")
        acceptance = RAGSystem._first_meta(md, "竣工验收单")
        address = RAGSystem._first_meta(md, "项目地址")
        return (
            f"签订合同时间：{signed}；年份：{year}；项目名称：{pname}；总监/项目经理：{director}；"
            f"合同金额(万元)：{contract_amt}；投资额(万元)：{invest_amt}；规模：{scale}；"
            f"委托单位：{client}；{pro_seg}；竣工时间：{completion}；"
            f"合同文件样式：{file_style}；竣工验收单：{acceptance}；项目地址：{address}；"
            f"描述：{doc.page_content}"
        )