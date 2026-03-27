import logging
from typing import Optional

from backend.app.core.tools.data_preprocessor import process_project_data_to_documents
from backend.app.core.tools.rag_system import RAGSystem

logger = logging.getLogger(__name__)

_rag_system = RAGSystem()
_rag_initialized = False


def get_rag_system() -> RAGSystem:
    return _rag_system


def ensure_rag_initialized() -> None:
    global _rag_initialized
    if _rag_initialized:
        return

    project_docs = process_project_data_to_documents()
    _rag_system.initialize_vector_store(project_docs, persist_directory="./chroma_db")
    _rag_initialized = True
    logger.info("RAG向量库初始化完成（共享运行时）")


def query_top1_context(query: str) -> str:
    ensure_rag_initialized()
    top1_doc: Optional = _rag_system.retrieve_top1(query=query)
    return _rag_system.format_doc_for_prompt(top1_doc)
