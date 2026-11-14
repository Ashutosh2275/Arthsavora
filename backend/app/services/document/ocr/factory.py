"""
Arthsavora OCR Engine Factory
Resolves the appropriate OCR engine based on environment, configuration, and MIME type.
"""

import os
from typing import Optional
from app.services.document.ocr.base_ocr import BaseOCREngine
from app.services.document.ocr.mock_ocr import MockDeterministicOCREngine
from app.services.document.ocr.pdf_text_extractor import PdfTextExtractor
from app.services.document.ocr.tesseract_ocr import TesseractOCREngine


def get_ocr_engine(
    provider: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> BaseOCREngine:
    """
    Returns the configured OCR engine.
    - If environment variable ARTHSAVORA_OCR_ENGINE == "mock" or provider == "mock", returns MockDeterministicOCREngine.
    - If mime_type == "application/pdf" and provider is not forced to mock or tesseract, returns PdfTextExtractor.
    - Otherwise defaults to TesseractOCREngine.
    """
    env_provider = os.getenv("ARTHSAVORA_OCR_ENGINE", "").lower()
    selected = (provider or env_provider or "").lower()

    if selected == "mock":
        return MockDeterministicOCREngine()

    if mime_type == "application/pdf" and selected != "tesseract":
        return PdfTextExtractor()

    return TesseractOCREngine()
