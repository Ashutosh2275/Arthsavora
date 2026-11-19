"""
Arthsavora Native PDF Text Extraction Engine
Extracts embedded digital text directly from vector PDF invoices and receipts using pypdf.
"""

import asyncio
import logging
from pathlib import Path

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

from app.services.document.ocr.base_ocr import BaseOCREngine, OCRRawResult

logger = logging.getLogger(__name__)


class PdfTextExtractor(BaseOCREngine):
    """Direct vector PDF text extractor for high-fidelity digital invoices."""

    async def extract_text(self, file_path: str, mime_type: str = "application/pdf") -> OCRRawResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_sync, file_path)

    def _extract_sync(self, file_path: str) -> OCRRawResult:
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"PDF document not found at {file_path}")

        try:
            page_texts = []
            page_count = 0
            provider_used = "native_pdf"

            if HAS_PYPDF:
                reader = PdfReader(src)
                page_count = len(reader.pages)
                provider_used = "pypdf_native"
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    page_texts.append(page_text)
            elif HAS_PDFPLUMBER:
                with pdfplumber.open(src) as pdf:
                    page_count = len(pdf.pages)
                    provider_used = "pdfplumber_native"
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        page_texts.append(page_text)
            else:
                raise RuntimeError("Neither pypdf nor pdfplumber is available for PDF extraction.")

            full_text = "\n\n--- Page Break ---\n\n".join(page_texts).strip()

            # Digital text has exceptionally high extraction confidence
            confidence = 0.95 if full_text else 0.10

            return OCRRawResult(
                text=full_text,
                confidence=confidence,
                provider=provider_used,
                version="1.0",
                page_count=page_count,
                metadata={"pages": page_count},
            )
        except Exception as e:
            logger.error(f"Native PDF extraction failed on {file_path}: {e}")
            raise RuntimeError(f"PDF extraction failed: {e}") from e
