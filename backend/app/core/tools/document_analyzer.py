import pytesseract
from PIL import Image
import cv2
import numpy as np
from io import BytesIO
import logging
from typing import Dict, Any, Optional, List
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置Tesseract路径
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class DocumentType:
    TEXT = 'TEXT'
    SEARCHABLE_PDF = 'SEARCHABLE_PDF'
    SCANNED_PDF = 'SCANNED_PDF'
    MIXED_PDF = 'MIXED_PDF'
    IMAGE = 'IMAGE'
    STRUCTURED_IMAGE = 'STRUCTURED_IMAGE'
    PDF = 'PDF'
    UNKNOWN = 'UNKNOWN'

class ProcessingStrategy:
    DIRECT_PARSE = 'DIRECT_PARSE'
    OCR_PROCESS = 'OCR_PROCESS'
    HYBRID_PROCESS = 'HYBRID_PROCESS'
    STRUCTURE_PARSE = 'STRUCTURE_PARSE'
    ERROR = 'ERROR'

class DocumentAnalysisResult:
    def __init__(self, document_type: str, strategy: str, confidence: float, metadata: Dict[str, Any], 
                 recommendations: Optional[list] = None, error: Optional[str] = None):
        self.document_type = document_type
        self.strategy = strategy
        self.confidence = confidence
        self.metadata = metadata
        self.recommendations = recommendations or []
        self.error = error

class DocumentTypeAnalyzer:
    def __init__(self):
        self.MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        self.MIN_FILE_SIZE = 100  # 100字节

    def analyze_document(self, file_content: bytes, file_name: str, file_size: int) -> DocumentAnalysisResult:
        try:
            # 1. 基础验证
            validation = self.validate_file(file_content, file_name, file_size)
            if validation['error']:
                return DocumentAnalysisResult(
                document_type=DocumentType.UNKNOWN, strategy=ProcessingStrategy.ERROR, confidence=0, metadata=validation['metadata'], 
                error=validation['error']
            )

            # 2. 基于文件扩展名的初步判断
            preliminary_type = self.get_preliminary_type(file_name)

            # 3. 深度内容分析
            content_analysis = self.analyze_file_content(file_content, preliminary_type)

            # 4. 综合判断与策略选择
            result = self.determine_strategy(content_analysis, validation['metadata'])

            return result

        except Exception as e:
            return DocumentAnalysisResult(
                DocumentType.UNKNOWN, ProcessingStrategy.ERROR, 0, 
                {'size': file_size, 'mimeType': 'unknown'}, 
                error=str(e)
            )

    def validate_file(self, file_content: bytes, file_name: str, file_size: int) -> Dict[str, Any]:
        # 文件大小检查
        if file_size < self.MIN_FILE_SIZE:
            return {
                'error': f'File size {file_size}B is too small (minimum {self.MIN_FILE_SIZE}B)',
                'metadata': {'size': file_size, 'mimeType': 'unknown'}
            }

        if file_size > self.MAX_FILE_SIZE:
            return {
                'error': f'File size {file_size}B exceeds maximum limit ({self.MAX_FILE_SIZE}B)',
                'metadata': {'size': file_size, 'mimeType': 'unknown'}
            }

        return {'error': None, 'metadata': {'size': file_size, 'mimeType': 'unknown'}}

    def get_preliminary_type(self, file_name: str) -> DocumentType:
        ext = file_name.lower()
        
        if ext.endswith('.pdf'):
            return DocumentType.PDF
        elif ext.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
            return DocumentType.IMAGE
        elif ext.endswith(('.txt', '.md', '.csv', '.json', '.xml')):
            return DocumentType.TEXT
        else:
            return DocumentType.UNKNOWN

    def analyze_file_content(self, file_content: bytes, preliminary_type: DocumentType) -> Dict[str, Any]:
        if preliminary_type == DocumentType.TEXT:
            return self.analyze_text_file(file_content)
        elif preliminary_type == DocumentType.PDF:
            return self.analyze_pdf_file(file_content)
        elif preliminary_type == DocumentType.IMAGE:
            return self.analyze_image_file(file_content)
        else:
            return {
                'document_type': DocumentType.UNKNOWN,
                'has_text': False,
                'has_images': False,
                'is_encrypted': False,
                'is_damaged': False,
                'confidence': 0
            }

    def bytes_to_string(self, bytes_data: bytes) -> str:
        """尝试将字节数据解码为字符串"""
        try:
            return bytes_data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return bytes_data.decode('latin-1')
            except UnicodeDecodeError:
                return ""

    def analyze_text_file(self, bytes_data: bytes) -> Dict[str, Any]:
        try:
            text = self.bytes_to_string(bytes_data)
            has_text = len(text.strip()) > 0

            return {
                'document_type': DocumentType.TEXT,
                'has_text': has_text,
                'has_images': False,
                'is_encrypted': False,
                'is_damaged': not has_text,
                'confidence': 0.9 if has_text else 0.6
            }
        except Exception as e:
            logger.error(f"分析文本文件错误: {e}")
            return {
                'document_type': DocumentType.UNKNOWN,
                'has_text': False,
                'has_images': False,
                'is_encrypted': False,
                'is_damaged': True,
                'confidence': 0.2
            }

    def is_pdf_signature(self, bytes_data: bytes) -> bool:
        """检查文件是否具有PDF签名"""
        return bytes_data.startswith(b'%PDF')

    def has_pdf_text_content(self, bytes_data: bytes) -> bool:
        """检查PDF是否包含可提取的文本内容"""
        try:
            reader = PdfReader(BytesIO(bytes_data))
            for page in reader.pages:
                if page.extract_text().strip():
                    return True
            return False
        except Exception as e:
            logger.warning(f"检查PDF文本内容失败: {e}")
            return False

    def has_pdf_image_content(self, bytes_data: bytes) -> bool:
        """检查PDF是否包含图像内容 (通过尝试转换为图像) """
        try:
            # 尝试转换第一页，如果成功则认为包含图像
            images = convert_from_bytes(bytes_data, first_page=1, last_page=1, grayscale=True)
            return len(images) > 0
        except Exception as e:
            logger.warning(f"检查PDF图像内容失败: {e}")
            return False

    def analyze_pdf_file(self, bytes_data: bytes) -> Dict[str, Any]:
        # 检查PDF文件头
        if not self.is_pdf_signature(bytes_data):
            return {
                'document_type': DocumentType.UNKNOWN,
                'has_text': False,
                'has_images': False,
                'is_encrypted': False,
                'is_damaged': True,
                'confidence': 0.1
            }

        # 检查是否包含文本
        has_text = self.has_pdf_text_content(bytes_data)
        # 检查是否包含图像
        has_images = self.has_pdf_image_content(bytes_data)

        is_encrypted = False  # 假设此处有检测加密的逻辑
        is_damaged = False  # 假设此处有检测损坏的逻辑

        if has_text and not has_images:
            return {
                'document_type': DocumentType.SEARCHABLE_PDF,
                'has_text': True,
                'has_images': False,
                'is_encrypted': is_encrypted,
                'is_damaged': is_damaged,
                'confidence': 0.95
            }
        elif has_images and not has_text:
            return {
                'document_type': DocumentType.SCANNED_PDF,
                'has_text': False,
                'has_images': True,
                'is_encrypted': is_encrypted,
                'is_damaged': is_damaged,
                'confidence': 0.9
            }
        elif has_text and has_images:
            return {
                'document_type': DocumentType.MIXED_PDF,
                'has_text': True,
                'has_images': True,
                'is_encrypted': is_encrypted,
                'is_damaged': is_damaged,
                'confidence': 0.9
            }
        else:
            # 如果既无文本也无图像，或者两者皆有但未能有效提取，可能仍然是扫描PDF或损坏文件
            return {
                'document_type': DocumentType.SCANNED_PDF, # 默认认为是扫描件，因为PyPDF2未提取到文本
                'has_text': False,
                'has_images': has_images, # 即使没文本，也可能只有图像
                'is_encrypted': is_encrypted,
                'is_damaged': is_damaged,
                'confidence': 0.5
            }

    def is_valid_image_signature(self, bytes_data: bytes) -> bool:
        """检查文件是否具有常见图片格式的签名"""
        # 简单的文件头检查
        # JPEG: FF D8 FF
        # PNG: 89 50 4E 47 0D 0A 1A 0A
        # GIF: 47 49 46 38
        # BMP: 42 4D
        if bytes_data.startswith(b'\xFF\xD8\xFF'): # JPEG
            return True
        if bytes_data.startswith(b'\x89PNG\x0D\x0A\x1A\x0A'): # PNG
            return True
        if bytes_data.startswith(b'GIF8'): # GIF
            return True
        if bytes_data.startswith(b'BM'): # BMP
            return True
        return False

    def analyze_image_file(self, bytes_data: bytes) -> Dict[str, Any]:
        if not self.is_valid_image_signature(bytes_data):
            return {
                'document_type': DocumentType.UNKNOWN,
                'has_text': False,
                'has_images': False,
                'is_encrypted': False,
                'is_damaged': True,
                'confidence': 0.1
            }

        # 假设所有有效的图片都包含图像，OCR工具会尝试提取文本
        return {
            'document_type': DocumentType.IMAGE,
            'has_text': False, # 初始假设无文本，依赖OCR
            'has_images': True,
            'is_encrypted': False,
            'is_damaged': False,
            'confidence': 0.9
        }

    def determine_strategy(self, content_analysis: Dict[str, Any], metadata: Dict[str, Any]) -> DocumentAnalysisResult:
        document_type = content_analysis.get('document_type', DocumentType.UNKNOWN)
        has_text = content_analysis.get('has_text', False)
        has_images = content_analysis.get('has_images', False)
        is_encrypted = content_analysis.get('is_encrypted', False)
        is_damaged = content_analysis.get('is_damaged', False)
        confidence = content_analysis.get('confidence', 0)

        if is_encrypted or is_damaged:
            return DocumentAnalysisResult(document_type, ProcessingStrategy.ERROR, confidence, metadata, error="文件加密或损坏")

        if document_type == DocumentType.TEXT:
            return DocumentAnalysisResult(document_type, ProcessingStrategy.DIRECT_PARSE, confidence, metadata)

        if document_type == DocumentType.IMAGE:
            return DocumentAnalysisResult(document_type, ProcessingStrategy.OCR_PROCESS, confidence, metadata)

        if document_type == DocumentType.SEARCHABLE_PDF:
            return DocumentAnalysisResult(document_type, ProcessingStrategy.DIRECT_PARSE, confidence, metadata)

        if document_type == DocumentType.SCANNED_PDF:
            return DocumentAnalysisResult(document_type, ProcessingStrategy.OCR_PROCESS, confidence, metadata)

        if document_type == DocumentType.MIXED_PDF:
            return DocumentAnalysisResult(document_type, ProcessingStrategy.HYBRID_PROCESS, confidence, metadata)

        # 默认回退
        return DocumentAnalysisResult(DocumentType.UNKNOWN, ProcessingStrategy.OCR_PROCESS, 0.5, metadata, recommendations=["尝试OCR处理"])

# 创建全局文档分析器实例
document_analyzer = DocumentTypeAnalyzer()
