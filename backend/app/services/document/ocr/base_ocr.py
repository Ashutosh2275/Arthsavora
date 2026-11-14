"""
Arthsavora Document Intelligence OCR Engine Interface
Standardizes provider-independent text and metadata extraction from documents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OCRRawResult:
    """Raw text extraction output from an optical character recognition engine."""
    text: str
    confidence: float  # 0.0 to 1.0
    provider: str
    version: Optional[str] = None
    page_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseOCREngine(ABC):
    """Abstract contract for OCR engines (Tesseract, Native PDF, Cloud Provider, Mock)."""

    @abstractmethod
    async def extract_text(self, file_path: str, mime_type: str = "image/png") -> OCRRawResult:
        """Extract raw text and confidence score from a local document file."""
        pass
