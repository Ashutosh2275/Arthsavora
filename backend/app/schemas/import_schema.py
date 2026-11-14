"""
Arthsavora Financial Data Acquisition & Import API Schemas
Pydantic DTOs for file uploads, preview candidates, candidate edits, and confirmation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ImportCandidateResponse(BaseModel):
    """Public representation of an imported transaction candidate."""
    id: uuid.UUID
    import_batch_id: uuid.UUID
    workspace_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    source_row_number: int
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    normalized_data: Dict[str, Any] = Field(default_factory=dict)
    validation_status: str  # valid, invalid, ambiguous, duplicate
    validation_errors: List[str] = Field(default_factory=list)
    duplicate_status: str  # none, exact, probable
    duplicate_match_id: Optional[uuid.UUID] = None
    duplicate_reason: Optional[str] = None
    confidence_score: Decimal = Decimal("1.00")
    review_status: str  # pending, accepted, rejected, edited
    selected_for_import: bool = True
    created_transaction_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ImportCandidateUpdateRequest(BaseModel):
    """Payload to modify review decisions or values of a candidate."""
    selected_for_import: Optional[bool] = None
    review_status: Optional[str] = None  # accepted, rejected, edited
    description: Optional[str] = None
    transaction_date: Optional[str] = None
    amount: Optional[Decimal] = None
    direction: Optional[str] = None
    transaction_type: Optional[str] = None
    category_id: Optional[uuid.UUID] = None


class ImportBatchResponse(BaseModel):
    """Public summary of a parsed statement batch."""
    id: uuid.UUID
    import_job_id: uuid.UUID
    workspace_id: uuid.UUID
    source_format: str
    sheet_name: Optional[str] = None
    row_count: int
    valid_row_count: int
    invalid_row_count: int
    duplicate_count: int
    processing_status: str
    column_mapping: Dict[str, str] = Field(default_factory=dict)
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    calculated_closing_balance: Optional[Decimal] = None
    reconciliation_difference: Optional[Decimal] = None
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class ImportJobSummary(BaseModel):
    """High-level summary of an import job."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    source_type: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    status: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    imported_records: int
    error_summary: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ImportUploadResponse(BaseModel):
    """Response returned upon successful file upload and parsing."""
    job_id: uuid.UUID
    batch_id: uuid.UUID
    status: str
    source_type: str
    original_filename: Optional[str] = None
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    available_sheets: List[str] = Field(default_factory=list)
    reconciliation: Dict[str, Any] = Field(default_factory=dict)
    candidates_preview: List[Dict[str, Any]] = Field(default_factory=list)


class ImportConfirmRequest(BaseModel):
    """Payload to confirm staged candidate import."""
    target_account_id: Optional[uuid.UUID] = None


class ImportConfirmResponse(BaseModel):
    """Response returned after transaction creation and ledger posting."""
    job_id: uuid.UUID
    status: str
    imported_count: int
    created_transaction_ids: List[uuid.UUID] = Field(default_factory=list)
    completed_at: Optional[str] = None


class ImportReconciliationReport(BaseModel):
    """Statement reconciliation comparison."""
    batch_id: uuid.UUID
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    total_inflows: Decimal = Decimal("0.0000")
    total_outflows: Decimal = Decimal("0.0000")
    calculated_closing_balance: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    is_reconciled: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class ImportJobListResponse(BaseModel):
    """Paginated list of import jobs."""
    items: List[ImportJobSummary]
    total: int
    limit: int
    offset: int


class ImportCandidateListResponse(BaseModel):
    """Paginated list of candidates in a batch."""
    items: List[ImportCandidateResponse]
    total: int
    limit: int
    offset: int
