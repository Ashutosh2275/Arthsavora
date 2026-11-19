"""
Arthsavora Financial Connection, Provider Registry & Aggregation Relational Models
PostgreSQL source of truth for Account Aggregator (AA) connections, ReBIT consent artefacts,
external account discovery references, sync checkpoints, and reconciliation audits.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.user import User
    from app.infrastructure.database.models.account import Account


class FinancialProvider(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Catalog of supported financial data providers (AAs, banking APIs, sandbox adapters)."""
    __tablename__ = "financial_providers"

    provider_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="account_aggregator", nullable=False)
    country: Mapped[str] = mapped_column(String(3), default="IN", nullable=False)
    supported_institutions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    supported_account_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    auth_method: Mapped[str] = mapped_column(String(50), default="consent_handle", nullable=False)
    consent_capabilities: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    data_capabilities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    historical_days_limit: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    sync_capabilities: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="sandbox_only", nullable=False)
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    docs_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    config_status: Mapped[str] = mapped_column(String(30), default="unconfigured", nullable=False)
    provider_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    connections: Mapped[List["FinancialConnection"]] = relationship("FinancialConnection", back_populates="provider")

    def __repr__(self) -> str:
        return f"<FinancialProvider code={self.provider_code} name={self.name} status={self.status}>"


class FinancialConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """User/Workspace connection to an external financial provider or institution."""
    __tablename__ = "financial_connections"
    __table_args__ = (
        Index("ix_fin_conn_workspace_status", "workspace_id", "status"),
        Index("ix_fin_conn_user", "user_id"),
    )

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
    provider_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_providers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    institution_id: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="initiated", nullable=False)
    health_status: Mapped[str] = mapped_column(String(30), default="needs_authorization", nullable=False)
    provider_connection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authorization_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempted_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_schedule: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    provider: Mapped["FinancialProvider"] = relationship("FinancialProvider", back_populates="connections")
    consents: Mapped[List["FinancialConsent"]] = relationship("FinancialConsent", back_populates="connection", cascade="all, delete-orphan")
    account_references: Mapped[List["ExternalAccountReference"]] = relationship("ExternalAccountReference", back_populates="connection", cascade="all, delete-orphan")
    sync_jobs: Mapped[List["SyncJob"]] = relationship("SyncJob", back_populates="connection", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FinancialConnection id={self.id} inst={self.institution_name} status={self.status}>"


class FinancialConsent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit ReBIT AA consent artefact and audit history."""
    __tablename__ = "financial_consents"
    __table_args__ = (
        Index("ix_fin_consent_workspace_status", "workspace_id", "status"),
        Index("ix_fin_consent_handle", "provider_consent_handle"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_consent_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str] = mapped_column(String(255), default="Personal Financial Management", nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(50), default="101", nullable=False)
    data_categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    account_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="initiated", nullable=False)
    fetch_frequency: Mapped[str] = mapped_column(String(30), default="PERIODIC", nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent_artefact_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    connection: Mapped["FinancialConnection"] = relationship("FinancialConnection", back_populates="consents")

    def __repr__(self) -> str:
        return f"<FinancialConsent id={self.id} status={self.status} valid_to={self.valid_to}>"


class ExternalAccountReference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """External accounts discovered from FIPs under an authorized consent."""
    __tablename__ = "external_account_references"
    __table_args__ = (
        Index("ix_ext_acc_conn", "connection_id"),
        Index("ix_ext_acc_workspace", "workspace_id"),
        UniqueConstraint("connection_id", "provider_account_id", name="uq_conn_provider_account"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    fip_id: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    masked_account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), default="savings", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="discovered", nullable=False)
    account_holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_balance_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    available_balance_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    balance_as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    connection: Mapped["FinancialConnection"] = relationship("FinancialConnection", back_populates="account_references")
    checkpoints: Mapped[List["SyncCheckpoint"]] = relationship("SyncCheckpoint", back_populates="account_reference", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ExternalAccountReference id={self.id} mask={self.masked_account_number} status={self.status}>"


class SyncJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Synchronization batch jobs tracking incremental data ingestion."""
    __tablename__ = "sync_jobs"
    __table_args__ = (
        Index("ix_sync_jobs_conn_status", "connection_id", "status"),
        Index("ix_sync_jobs_workspace", "workspace_id"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_type: Mapped[str] = mapped_column(String(50), default="manual_sync", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_retrieved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checkpoint_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    connection: Mapped["FinancialConnection"] = relationship("FinancialConnection", back_populates="sync_jobs")

    def __repr__(self) -> str:
        return f"<SyncJob id={self.id} type={self.job_type} status={self.status} imported={self.records_imported}>"


class SyncCheckpoint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent cursor tracking the high-water mark for incremental synchronization."""
    __tablename__ = "sync_checkpoints"
    __table_args__ = (
        Index("ix_sync_chk_conn", "connection_id"),
        UniqueConstraint("connection_id", "external_account_ref_id", name="uq_conn_account_checkpoint"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_account_ref_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("external_account_references.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_sync_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_transaction_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checkpoint_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    account_reference: Mapped["ExternalAccountReference"] = relationship("ExternalAccountReference", back_populates="checkpoints")

    def __repr__(self) -> str:
        return f"<SyncCheckpoint id={self.id} last_tx_date={self.last_transaction_date}>"


class ReconciliationRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reconciliation audit comparing provider reported balance against book balance."""
    __tablename__ = "reconciliation_records"
    __table_args__ = (
        Index("ix_rec_records_account", "account_id"),
        Index("ix_rec_records_workspace", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    reconciliation_date: Mapped[date] = mapped_column(Date, nullable=False)
    provider_reported_balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    calculated_book_balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    difference_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="matched", nullable=False)
    unmatched_transactions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ReconciliationRecord id={self.id} status={self.status} diff={self.difference_paise}>"


class ConnectionAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit trail of connection life-cycle, consent state, and synchronization events."""
    __tablename__ = "connection_audit_events"
    __table_args__ = (
        Index("ix_conn_audit_workspace", "workspace_id"),
        Index("ix_conn_audit_conn", "connection_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<ConnectionAuditEvent type={self.event_type} severity={self.severity}>"
