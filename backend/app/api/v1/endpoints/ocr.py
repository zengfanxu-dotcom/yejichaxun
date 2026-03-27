from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket
import os
import tempfile
from backend.app.core.tools.ocr_tool import ocr_tool, OCRResult

router = APIRouter()

@router.post("/ocr/process", response_model=OCRResult)
async def process_ocr(file: UploadFile = File(...)):
    """处理OCR请求"""
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        # 处理OCR
        file_name = file.filename or "unknown"
        file_size = len(content)
        text = ocr_tool.extract_text(content, file_name, file_size)
        
        # 清理临时文件
        os.remove(temp_path)
        
        return OCRResult(text=text)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR处理失败: {str(e)}")

# 添加WebSocket端点（可选）
@router.websocket("/ocr/process/ws")
async def websocket_ocr(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 处理WebSocket消息
            await websocket.send_text(f"收到: {data}")
    except Exception as e:
        print(f"WebSocket错误: {e}")
    finally:
        await websocket.close()