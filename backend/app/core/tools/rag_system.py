import logging
from typing import List, Optional

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGSystem:
    """
    最小RAG实现（可扩展）：
    query -> embedding -> Chroma -> top1 -> 上层拼接prompt
    """

    def __init__(self, embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_model = HuggingFaceEmbeddings(model_name=embedding_model_name)
        self.vector_store: Optional[Chroma] = None

    def initialize_vector_store(self, documents: List[Document], persist_directory: Optional[str] = None):
        if not documents:
            logger.warning("初始化向量库时文档为空，跳过。")
            return

        logger.info("正在初始化向量存储...")
        if persist_directory:
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                persist_directory=persist_directory,
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

    def retrieve_top1(self, query: str) -> Optional[Document]:
        docs = self.similarity_search(query=query, k=1)
        return docs[0] if docs else None

    @staticmethod
    def format_doc_for_prompt(doc: Optional[Document]) -> str:
        if not doc:
            return "无可用检索结果"
        project_name = doc.metadata.get("project_name", "")
        year = doc.metadata.get("year", "")
        amount = doc.metadata.get("amount", "")
        project_type = doc.metadata.get("type", "")
        manager = doc.metadata.get("manager", "")
        return (
            f"候选业绩：{project_name}；年份：{year}；金额(万元)：{amount}；"
            f"类型：{project_type}；项目经理：{manager}；"
            f"描述：{doc.page_content}"
        )