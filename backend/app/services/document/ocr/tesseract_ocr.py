"""
Arthsavora Tesseract OCR Engine Implementation
Leverages Open Source Tesseract OCR engine with automatic binary detection,
word confidence aggregation, and multi-language support (English + Indic).
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from PIL import Image
import pytesseract

from app.services.document.ocr.base_ocr import BaseOCREngine, OCRRawResult

logger = logging.getLogger(__name__)

# Standard Windows installation paths for Tesseract
WINDOWS_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
]


def configure_tesseract_binary():
    """Autodetect and configure tesseract binary on host."""
    current_cmd = pytesseract.pytesseract.tesseract_cmd
    if os.path.exists(current_cmd) and not current_cmd.endswith("tesseract"):
        return

    for path in WINDOWS_TESSERACT_PATHS:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Configured Tesseract binary at {path}")
            return


configure_tesseract_binary()


class TesseractOCREngine(BaseOCREngine):
    """Production Tesseract engine with word-level confidence evaluation."""

    def __init__(self, lang: str = "eng"):
        self.lang = lang
        configure_tesseract_binary()

    async def extract_text(self, file_path: str, mime_type: str = "image/png") -> OCRRawResult:
        """Run Tesseract character recognition in an async thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_sync, file_path)

    def _extract_sync(self, file_path: str) -> OCRRawResult:
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"Image for OCR not found at {file_path}")

        try:
            with Image.open(src) as img:
                # 1. Extract detailed word data with confidence
                data = pytesseract.image_to_data(
                    img,
                    lang=self.lang,
                    output_type=pytesseract.Output.DICT,
                )

                # 2. Extract full raw text
                text = pytesseract.image_to_string(img, lang=self.lang)

                # 3. Calculate average confidence from valid words
                confs = [int(c) for c in data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
                avg_conf = (sum(confs) / (len(confs) * 100.0)) if confs else 0.50

                try:
                    version = str(pytesseract.get_tesseract_version())
                except Exception:
                    version = "5.x"

                return OCRRawResult(
                    text=text.strip(),
                    confidence=round(avg_conf, 4),
                    provider="tesseract",
                    version=version,
                    page_count=1,
                    metadata={"word_count": len(confs)},
                )
        except Exception as e:
            logger.error(f"Tesseract OCR extraction failed on {file_path}: {e}")
            raise RuntimeError(f"Tesseract OCR failed: {e}") from e
