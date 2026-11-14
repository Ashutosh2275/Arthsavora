"""
Arthsavora Native PDF Text Extraction Engine
Extracts embedded digital text directly from vector PDF invoices and receipts using pypdf.
"""

import asyncio
import logging
from pathlib import Path
from pypdf import PdfReader

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
            reader = PdfReader(src)
            page_texts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_texts.append(page_text)

            full_text = "\n\n--- Page Break ---\n\n".join(page_texts).strip()

            # Digital text has exceptionally high extraction confidence
            confidence = 0.95 if full_text else 0.10

            return OCRRawResult(
                text=full_text,
                confidence=confidence,
                provider="pypdf_native",
                version="pypdf",
                page_count=len(reader.pages),
                metadata={"pages": len(reader.pages)},
            )
        except Exception as e:
            logger.error(f"Native PDF extraction failed on {file_path}: {e}")
            raise RuntimeError(f"PDF extraction failed: {e}") from e
