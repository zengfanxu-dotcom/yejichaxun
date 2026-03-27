import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.tools.rag_runtime import query_top1_context

logger = logging.getLogger(__name__)
router = APIRouter()


class RAGQueryRequest(BaseModel):
    query: str


class RAGQueryResponse(BaseModel):
    query: str
    top1_context: str


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(payload: RAGQueryRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")

    try:
        top1_context = query_top1_context(query=query)
        return RAGQueryResponse(query=query, top1_context=top1_context)
    except Exception as e:
        logger.error("RAG查询失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG查询失败: {str(e)}")
