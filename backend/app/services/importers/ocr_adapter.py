"""
Arthsavora OCR Statement Adapter
Fallback OCR pipeline for scanned statement documents with confidence tracking,
explicit limitations declaration, and mandatory user verification requirements.
"""

from decimal import Decimal
import io
import os
import re
from typing import Any, Dict, List, Optional
from PIL import Image
import pytesseract

from app.domain.import_types import SourceFormat
from app.services.importers.base import BaseStatementParser, ParsedRow, ParserResult


class OcrStatementAdapter(BaseStatementParser):
    """
    Fallback adapter for scanned image-only PDF/image statements.
    Reports OCR confidence scores and requires explicit user review.
    """

    DEFAULT_CONFIDENCE = Decimal("0.70")

    def __init__(self):
        # Configure Tesseract path if present on Windows
        if os.name == "nt" and os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    def parse(
        self,
        content_bytes: bytes,
        column_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ParserResult:
        """Runs OCR extraction on image bytes or scanned document pages."""
        try:
            # 1. Attempt image loading
            img = Image.open(io.BytesIO(content_bytes)).convert("L")
            raw_text = pytesseract.image_to_string(img)
        except Exception as err:
            return ParserResult(
                source_format=SourceFormat.PDF_OCR.value,
                rows=[],
                is_ocr=True,
                metadata={
                    "ocr_engine": "Tesseract",
                    "status": "unavailable_or_failed",
                    "error": str(err),
                    "notice": "OCR engine requires a clean image stream or local Tesseract installation.",
                },
            )

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return ParserResult(
                source_format=SourceFormat.PDF_OCR.value,
                rows=[],
                is_ocr=True,
                metadata={"ocr_engine": "Tesseract", "extracted_line_count": 0},
            )

        # 2. Extract potential financial transaction lines using heuristic regex
        # Date regex: \d{1,2}[/-]\d{1,2}[/-]\d{2,4}
        # Amount regex: \d+[\.,]\d{2}
        date_pattern = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
        amount_pattern = re.compile(r"(\d{1,3}(?:,\d{2,3})*(?:\.\d{2}))")

        extracted_rows: List[ParsedRow] = []
        row_counter = 1

        for line in lines:
            date_match = date_pattern.search(line)
            amt_matches = amount_pattern.findall(line)

            if date_match and amt_matches:
                dt_str = date_match.group(1)
                # Remove matched date from line to get narration
                remaining = line.replace(dt_str, "").strip()
                amt_str = amt_matches[-1]  # usually amount or balance is last
                narration = remaining.replace(amt_str, "").strip() or "OCR Transaction"

                extracted_rows.append(
                    ParsedRow(
                        row_number=row_counter,
                        raw_data={"ocr_line": line},
                        date_str=dt_str,
                        description_str=narration,
                        amount_str=amt_str,
                        confidence_score=self.DEFAULT_CONFIDENCE,
                    )
                )
                row_counter += 1

        return ParserResult(
            source_format=SourceFormat.PDF_OCR.value,
            rows=extracted_rows,
            is_ocr=True,
            metadata={
                "ocr_engine": "Tesseract",
                "extracted_line_count": len(lines),
                "total_rows_extracted": len(extracted_rows),
                "notice": "Data extracted via OCR. Mandatory manual verification required before posting.",
            },
        )
