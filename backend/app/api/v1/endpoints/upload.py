from fastapi import APIRouter, UploadFile, File, HTTPException
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入 analyzer、OCR工具和RAG相关模块
from backend.app.core.agent.analyzer import analyze_tender
from backend.app.core.tools.ocr_tool import ocr_tool
from backend.app.core.tools.rag_runtime import query_top1_context

router = APIRouter()

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        logger.info(f"开始处理文件: {file.filename}")
        
        # 1. 读取文件 bytes
        content = await file.read()
        logger.info(f"文件大小: {len(content)} bytes")
        
        # 2. 分析文档类型并选择处理策略
        file_name = file.filename or "unknown"
        file_size = len(content)
        
        # 分析文档类型
        analysis = ocr_tool.analyze_document(content, file_name, file_size)
        document_type = analysis['document_type']
        strategy = analysis['strategy']
        confidence = analysis['confidence']
        
        logger.info(f"文档类型: {document_type}, 处理策略: {strategy}, 置信度: {confidence:.2f}")
        
        # 3. 文本提取（统一入口，内部自动路由 DIRECT_PARSE/OCR/HYBRID）
        text = ocr_tool.extract_text(content, file_name, file_size)
        
        logger.info(f"提取的总文本长度: {len(text)} 字符")
        
        if text:
            logger.info(f"最终文本前100字符: {text[:100]}...")
        else:
            logger.error("未提取到任何文本内容")
            raise HTTPException(
                status_code=400, 
                detail="无法从文件中提取文本内容，请检查文件是否包含可识别的文字"
            )
        
        # 4. 最小RAG链路：query -> embedding -> Chroma -> top1 -> prompt拼接
        rag_context = query_top1_context(query=text[:1000])

        # 5. 调用分析函数（带RAG上下文）
        result = analyze_tender(text=text, rag_context=rag_context)
        logger.info(f"分析结果: {result}")

        # 6. 返回结构化结果 + 简要检索信息（便于调试和后续扩展）
        return {
            **result,
            "rag_top1_context": rag_context
        }
        
    except Exception as e:
        # 避免 f-string 尝试解析异常信息中的花括号
        logger.error("处理文件时发生错误: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")