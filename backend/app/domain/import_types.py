"""
Arthsavora Financial Data Acquisition & Import Types
Domain enumerations, constants, bank header mappings, and validation rules.
"""

from enum import Enum
from typing import Dict, List, Set


class ImportStatus(str, Enum):
    """Lifecycle statuses for statement and data acquisition jobs."""
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    CONFIRMED = "confirmed"
    PARTIALLY_CONFIRMED = "partially_confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ImportSourceType(str, Enum):
    """High-level origin category of financial data files."""
    CSV = "csv"
    XLSX = "xlsx"
    PDF_STATEMENT = "pdf_statement"
    CREDIT_CARD_STATEMENT = "credit_card_statement"
    MANUAL = "manual"


class SourceFormat(str, Enum):
    """Specific technical parser adapter format."""
    CSV = "csv"
    XLSX = "xlsx"
    PDF_TEXT = "pdf_text"
    PDF_OCR = "pdf_ocr"
    MANUAL = "manual"


class ValidationStatus(str, Enum):
    """Row-level candidate validation verdict."""
    VALID = "valid"
    INVALID = "invalid"
    AMBIGUOUS = "ambiguous"
    DUPLICATE = "duplicate"


class DuplicateStatus(str, Enum):
    """Deduplication classification against existing ledger records."""
    NONE = "none"
    EXACT = "exact"
    PROBABLE = "probable"


class ReviewStatus(str, Enum):
    """User review decision for a candidate row."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


# ---------------------------------------------------------------------------
# File Security & Parser Constraints
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_EXTENSIONS: Set[str] = {".csv", ".xlsx", ".pdf"}
ALLOWED_MIME_TYPES: Set[str] = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/pdf",
    "text/plain",
    "application/octet-stream",  # Fallback MIME for some browsers
}

FILE_MAGIC_SIGNATURES: Dict[str, bytes] = {
    "pdf": b"%PDF-",
    "xlsx": b"PK\x03\x04",
}

# ---------------------------------------------------------------------------
# Common Indian Banking Header Synonym Mappings
# ---------------------------------------------------------------------------

HEADER_SYNONYMS: Dict[str, List[str]] = {
    "date": [
        "date", "txn date", "txndate", "transaction date", "tran date",
        "post date", "posting date", "entry date", "value date"
    ],
    "description": [
        "narration", "description", "particulars", "remarks", "transaction remarks",
        "details", "transaction details", "party name", "memo"
    ],
    "ref_no": [
        "chq/ref no", "chq./ref.no.", "chq no", "cheque no", "cheque.no.", "chqno",
        "ref no", "ref no.", "reference number", "ref no./cheque no.", "utr",
        "transaction id", "txn id", "transaction ref"
    ],
    "debit": [
        "debit", "withdrawal", "withdrawal amt.", "withdrawal amount (inr )",
        "withdrawal amount", "dr", "dr amount", "paid out", "debit amount"
    ],
    "credit": [
        "credit", "deposit", "deposit amt.", "deposit amount (inr )",
        "deposit amount", "cr", "cr amount", "paid in", "credit amount"
    ],
    "amount": [
        "amount", "txn amount", "transaction amount", "net amount", "amt"
    ],
    "balance": [
        "balance", "closing balance", "bal", "available balance", "balance (inr )",
        "running balance", "account balance"
    ],
}

# Specific Bank Presets for Deterministic Matching
BANK_MAPPINGS: Dict[str, Dict[str, str]] = {
    "hdfc": {
        "date": "Date",
        "description": "Narration",
        "ref_no": "Chq./Ref.No.",
        "debit": "Withdrawal Amt.",
        "credit": "Deposit Amt.",
        "balance": "Closing Balance",
    },
    "sbi": {
        "date": "Txn Date",
        "description": "Description",
        "ref_no": "Ref No./Cheque No.",
        "debit": "Debit",
        "credit": "Credit",
        "balance": "Balance",
    },
    "icici": {
        "date": "Transaction Date",
        "description": "Transaction Remarks",
        "ref_no": "Cheque.No.",
        "debit": "Withdrawal Amount (INR )",
        "credit": "Deposit Amount (INR )",
        "balance": "Balance (INR )",
    },
    "axis": {
        "date": "Tran Date",
        "description": "PARTICULARS",
        "ref_no": "CHQNO",
        "debit": "DR",
        "credit": "CR",
        "balance": "BAL",
    },
    "kotak": {
        "date": "Transaction Date",
        "description": "Description",
        "ref_no": "Ref / Chq No",
        "debit": "Debit",
        "credit": "Credit",
        "balance": "Balance",
    },
}
