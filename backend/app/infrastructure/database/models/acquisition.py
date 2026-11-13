"""
Arthsavora Financial Data Acquisition, Consent & Import Models
PostgreSQL source of truth for external data sources, user consent governance, and idempotent file imports.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, text
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
    """Tracks batch transaction and document ingestion jobs with provenance and error telemetry."""
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
    )
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # sms, csv, pdf_statement, api
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending, processing, completed, failed
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    files: Mapped[list["ImportFile"]] = relationship("ImportFile", back_populates="import_job", cascade="all, delete-orphan")

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
