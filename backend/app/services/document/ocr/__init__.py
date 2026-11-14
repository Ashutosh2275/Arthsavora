"""
Arthsavora Document Intelligence OCR Engines
"""

from app.services.document.ocr.base_ocr import BaseOCREngine, OCRRawResult
from app.services.document.ocr.factory import get_ocr_engine
from app.services.document.ocr.mock_ocr import MockDeterministicOCREngine, SAMPLE_INDIAN_RECEIPTS
from app.services.document.ocr.pdf_text_extractor import PdfTextExtractor
from app.services.document.ocr.tesseract_ocr import TesseractOCREngine

__all__ = [
    "BaseOCREngine",
    "OCRRawResult",
    "TesseractOCREngine",
    "PdfTextExtractor",
    "MockDeterministicOCREngine",
    "SAMPLE_INDIAN_RECEIPTS",
    "get_ocr_engine",
]
