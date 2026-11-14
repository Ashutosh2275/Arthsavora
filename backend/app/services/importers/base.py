"""
Arthsavora Statement Parser Base Classes & Contracts
Defines standardized data classes and abstract parser contracts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class ParsedRow:
    """Raw parsed row from a statement prior to normalization and validation."""
    row_number: int
    raw_data: Dict[str, str]
    date_str: Optional[str] = None
    description_str: Optional[str] = None
    amount_str: Optional[str] = None
    debit_str: Optional[str] = None
    credit_str: Optional[str] = None
    balance_str: Optional[str] = None
    ref_str: Optional[str] = None
    category_hint: Optional[str] = None
    confidence_score: Decimal = Decimal("1.00")


@dataclass
class ParserResult:
    """Complete result returned by a statement parser."""
    source_format: str  # csv, xlsx, pdf_text, pdf_ocr, manual
    rows: List[ParsedRow] = field(default_factory=list)
    sheet_name: Optional[str] = None
    available_sheets: List[str] = field(default_factory=list)
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    account_number: Optional[str] = None
    statement_period: Optional[str] = None
    column_mapping_used: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_ocr: bool = False


class BaseStatementParser(ABC):
    """Abstract interface for all financial statement parsers."""

    @abstractmethod
    def parse(
        self,
        content_bytes: bytes,
        column_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ParserResult:
        """Parses file bytes into structured ParserResult."""
        pass
