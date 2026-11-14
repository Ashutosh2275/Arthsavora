"""
Arthsavora Document Intelligence & Receipt Extraction Relational Models
PostgreSQL source of truth for uploaded receipts, invoices, OCR extraction results,
field confidence vectors, user review records, and transaction associations.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.transaction import Transaction
    from app.infrastructure.database.models.user import User
    from app.infrastructure.database.models.workspace import Workspace


class FinancialDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authoritative metadata and file pointer for an uploaded receipt, invoice, or financial document."""
    __tablename__ = "financial_documents"
    __table_args__ = (
        Index("ix_documents_workspace_status", "workspace_id", "status"),
        Index("ix_documents_workspace_created", "workspace_id", "created_at"),
        Index("ix_documents_file_checksum", "workspace_id", "file_checksum"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    document_type: Mapped[str] = mapped_column(String(50), default="receipt", nullable=False)  # receipt, invoice, bill, supporting_doc
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, preprocessing, processing, extracted, review_required, confirmed, rejected, failed
    preprocessing_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    retention_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    extractions: Mapped[List["DocumentExtractionResult"]] = relationship(
        "DocumentExtractionResult",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentExtractionResult.created_at.desc()",
    )
    reviews: Mapped[List["DocumentReviewRecord"]] = relationship(
        "DocumentReviewRecord",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentReviewRecord.created_at.desc()",
    )
    transaction_associations: Mapped[List["DocumentTransactionAssociation"]] = relationship(
        "DocumentTransactionAssociation",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FinancialDocument id={self.id} filename={self.original_filename} status={self.status}>"


class DocumentExtractionResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Raw OCR text and structured financial entities extracted from a document with confidence metrics."""
    __tablename__ = "document_extractions"
    __table_args__ = (
        Index("ix_extractions_document_created", "document_id", "created_at"),
        Index("ix_extractions_workspace_id", "workspace_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ocr_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # tesseract, pdf_native, mock_engine
    ocr_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    field_confidences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    overall_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.0"), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), default="valid", nullable=False)  # valid, warning, invalid_math, incomplete
    validation_warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    document: Mapped["FinancialDocument"] = relationship("FinancialDocument", back_populates="extractions")

    def __repr__(self) -> str:
        return f"<DocumentExtractionResult id={self.id} doc_id={self.document_id} provider={self.ocr_provider} confidence={self.overall_confidence}>"


class DocumentReviewRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit log of user review actions, field corrections, and confirmation/rejection before ledger mutation."""
    __tablename__ = "document_reviews"
    __table_args__ = (
        Index("ix_reviews_document_created", "document_id", "created_at"),
        Index("ix_reviews_workspace_id", "workspace_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    corrected_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    review_action: Mapped[str] = mapped_column(String(50), nullable=False)  # confirmed, edited, rejected
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["FinancialDocument"] = relationship("FinancialDocument", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<DocumentReviewRecord id={self.id} doc_id={self.document_id} action={self.review_action}>"


class DocumentTransactionAssociation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Bidirectional linkage between a financial document and an authoritative financial transaction."""
    __tablename__ = "document_transaction_associations"
    __table_args__ = (
        Index("ix_doc_tx_assoc_document", "document_id"),
        Index("ix_doc_tx_assoc_transaction", "transaction_id"),
        Index("ix_doc_tx_assoc_workspace", "workspace_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    association_type: Mapped[str] = mapped_column(
        String(50),
        default="created_from_receipt",
        nullable=False,
    )  # created_from_receipt, matched_existing, manual_attachment
    match_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    match_evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    document: Mapped["FinancialDocument"] = relationship(
        "FinancialDocument",
        back_populates="transaction_associations",
    )
    transaction: Mapped["Transaction"] = relationship("Transaction")

    def __repr__(self) -> str:
        return f"<DocumentTransactionAssociation id={self.id} doc={self.document_id} tx={self.transaction_id} type={self.association_type}>"
