"""
Arthsavora Financial Data Acquisition, Consent & Import Models
PostgreSQL source of truth for external data sources, user consent governance,
and idempotent statement/batch imports with candidate review workflows.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class DataSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """External data origin connection (e.g. UPI SMS sync, manual CSV, bank statement parser)."""
    __tablename__ = "data_sources"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)  # manual, upi_sms, statement_pdf, email_sync
    connection_type: Mapped[str] = mapped_column(String(50), nullable=False)  # manual, sms_sync, statement_upload, aa_consent
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)  # active, inactive, error, revoked
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # Sanitized provider metadata; zero credentials

    def __repr__(self) -> str:
        return f"<DataSource id={self.id} name={self.name} provider={self.provider_name}>"


class ConsentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit financial data acquisition consent record with validity and revocation tracking."""
    __tablename__ = "consent_records"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    data_categories: Mapped[list] = mapped_column(JSONB, nullable=False)  # e.g. ["transactions", "balances"]
    source_or_recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    consent_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    expiry_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, expired, revoked
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<ConsentRecord id={self.id} purpose={self.purpose} status={self.status}>"


class ImportJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks batch transaction and document ingestion jobs with provenance, status machine and error telemetry."""
    __tablename__ = "import_jobs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv, xlsx, pdf_statement, credit_card_statement, manual
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Lifecycle: uploaded, validating, processing, awaiting_review, confirmed, partially_confirmed, completed, failed, cancelled, expired
    status: Mapped[str] = mapped_column(String(30), default="uploaded", nullable=False, index=True)
    
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Legacy compatibility aliases
    success_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    files: Mapped[list["ImportFile"]] = relationship("ImportFile", back_populates="import_job", cascade="all, delete-orphan")
    batches: Mapped[list["ImportBatch"]] = relationship("ImportBatch", back_populates="import_job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ImportJob id={self.id} type={self.source_type} status={self.status} total={self.total_records}>"


class ImportFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Storage and cryptographic hash tracking for imported statement and receipt files."""
    __tablename__ = "import_files"

    import_job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 for idempotency

    import_job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="files")

    def __repr__(self) -> str:
        return f"<ImportFile id={self.id} file={self.file_name} hash={self.file_hash[:10]}...>"


class ImportBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a discrete extraction batch within an import job (e.g. workbook sheet, statement segment)."""
    __tablename__ = "import_batches"

    import_job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_format: Mapped[str] = mapped_column(String(30), nullable=False)  # csv, xlsx, pdf_text, pdf_ocr, manual
    sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(30), default="extracted", nullable=False)  # extracted, normalized, validated, confirmed, failed
    column_mapping: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    calculated_closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    reconciliation_difference: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    import_job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="batches")
    candidates: Mapped[list["ImportCandidate"]] = relationship("ImportCandidate", back_populates="batch", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ImportBatch id={self.id} format={self.source_format} rows={self.row_count}>"


class ImportCandidate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Staged, parsed transaction candidate pending user review and confirmation before ledger posting."""
    __tablename__ = "import_candidates"

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    normalized_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(30), default="valid", nullable=False, index=True)  # valid, invalid, ambiguous, duplicate
    validation_errors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    duplicate_status: Mapped[str] = mapped_column(String(30), default="none", nullable=False, index=True)  # none, exact, probable
    duplicate_match_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    duplicate_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"), nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)  # pending, accepted, rejected, edited
    selected_for_import: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    batch: Mapped["ImportBatch"] = relationship("ImportBatch", back_populates="candidates")

    def __repr__(self) -> str:
        return f"<ImportCandidate id={self.id} row={self.source_row_number} status={self.validation_status} review={self.review_status}>"
