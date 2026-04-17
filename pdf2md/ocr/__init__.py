"""OCR engines for pdf2md."""

from pdf2md.ocr.base import OCRResult, OCREngine
from pdf2md.ocr.paddleocr import PaddleOCREngine

__all__ = ["OCREngine", "OCRResult", "PaddleOCREngine"]