import pytesseract
from PIL import Image
import cv2
import numpy as np
from io import BytesIO
import logging
from pydantic import BaseModel
from PyPDF2 import PdfReader 
from pdf2image import convert_from_bytes 
from backend.app.core.tools.document_analyzer import document_analyzer, DocumentType, ProcessingStrategy 

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置Tesseract路径
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class OCRResult(BaseModel):
    text: str


class OCRTool:
    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """图像预处理：灰度 + 二值化"""
        img = np.array(image)

        # 灰度转换
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 二值化
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        return thresh

    def analyze_document(self, file_bytes: bytes, file_name: str, file_size: int) -> dict:
        """分析文档类型并返回处理策略"""
        try:
            result = document_analyzer.analyze_document(file_bytes, file_name, file_size)
            # Ensure DocumentType and ProcessingStrategy are converted to their string values if needed by consumers
            return {
                'document_type': result.document_type,
                'strategy': result.strategy,
                'confidence': result.confidence,
                'has_text': result.metadata.get('hasText'), 
                'has_images': result.metadata.get('hasImages'), 
                'is_encrypted': result.metadata.get('isEncrypted'), 
                'is_damaged': result.metadata.get('isDamaged') 
            }
        except Exception as e:
            logger.error(f"文档分析错误: {e}", exc_info=True)
            return {
                'document_type': DocumentType.UNKNOWN,
                'strategy': ProcessingStrategy.ERROR,
                'confidence': 0,
                'has_text': False,
                'has_images': False,
                'is_encrypted': False,
                'is_damaged': True
            }

    def extract_text_from_image(self, file_bytes: bytes) -> str:
        """从图片中提取文本（带预处理）"""
        try:
            image = Image.open(BytesIO(file_bytes)).convert("RGB")
            processed = self.preprocess_image(image)

            text = pytesseract.image_to_string(
                processed,
                lang="chi_sim",
                config="--psm 6"
            )

            return text.strip()
        except Exception as e:
            logger.error(f"图像OCR处理错误: {e}", exc_info=True)
            return ""

    def _extract_text_from_pdf_internal(self, file_bytes: bytes, strategy: ProcessingStrategy) -> str:
        """内部方法：根据策略从PDF字节中提取文本"""
        text = ""
        try:
            if strategy == ProcessingStrategy.DIRECT_PARSE:
                pdf_file = BytesIO(file_bytes)
                reader = PdfReader(pdf_file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            elif strategy == ProcessingStrategy.OCR_PROCESS:
                images = convert_from_bytes(file_bytes)
                for img in images:
                    processed = self.preprocess_image(img)
                    page_text = pytesseract.image_to_string(
                        processed,
                        lang="chi_sim",
                        config="--psm 6"
                    )
                    text += page_text + "\n"
            elif strategy == ProcessingStrategy.HYBRID_PROCESS:
                # 先尝试直接提取文本
                pdf_file = BytesIO(file_bytes)
                reader = PdfReader(pdf_file)
                direct_text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        direct_text += page_text + "\n"
                text += direct_text

                # 如果直接提取的文本较少，则进行OCR
                if len(direct_text.strip()) < 50: # Arbitrary threshold, can be refined
                    images = convert_from_bytes(file_bytes)
                    for img in images:
                        processed = self.preprocess_image(img)
                        page_text = pytesseract.image_to_string(
                            processed,
                            lang="chi_sim",
                            config="--psm 6"
                        )
                        text += page_text + "\n"
            else:
                logger.warning(f"未知或不支持的PDF处理策略: {strategy}. 尝试OCR处理。")
                # Fallback to OCR if strategy is not recognized or is ERROR/UNKNOWN
                images = convert_from_bytes(file_bytes)
                for img in images:
                    processed = self.preprocess_image(img)
                    page_text = pytesseract.image_to_string(
                        processed,
                        lang="chi_sim",
                        config="--psm 6"
                    )
                    text += page_text + "\n"
        except Exception as e:
            logger.error(f"PDF内部文本提取错误 (策略: {strategy}): {e}", exc_info=True)
            text = "" 
        return text.strip()


    def extract_text(self, file_bytes: bytes, file_name: str, file_size: int) -> str:
        """统一的文本提取方法：根据文档分析结果选择最佳策略"""
        analysis = self.analyze_document(file_bytes, file_name, file_size)
        document_type = analysis['document_type']
        strategy = analysis['strategy']
        
        logger.info(f"统一提取器 - 文档类型: {document_type}, 策略: {strategy}")

        text = ""
        try:
            if strategy == ProcessingStrategy.ERROR:
                logger.error(f"文档分析指示错误策略，无法提取文本。错误: {analysis.get('error', '未知错误')}")
                return ""
            elif document_type == DocumentType.TEXT:
                text = file_bytes.decode('utf-8', errors='ignore')
            elif document_type in [DocumentType.PDF, DocumentType.SEARCHABLE_PDF, DocumentType.SCANNED_PDF, DocumentType.MIXED_PDF]:
                text = self._extract_text_from_pdf_internal(file_bytes, strategy)
            elif document_type == DocumentType.IMAGE:
                text = self.extract_text_from_image(file_bytes)
            elif document_type == DocumentType.UNKNOWN:
                logger.warning("文档类型未知，尝试OCR处理。")
                text = self.extract_text_from_image(file_bytes) 
                if not text:
                    text = self._extract_text_from_pdf_internal(file_bytes, ProcessingStrategy.OCR_PROCESS)
            else:
                logger.error(f"不支持的文档类型或策略组合: {document_type} / {strategy}")
                return ""
        except Exception as e:
            logger.error(f"统一文本提取器发生错误: {e}", exc_info=True)
            return ""
        
        return text.strip() if text else ""

# 创建全局OCR工具实例
ocr_tool = OCRTool()