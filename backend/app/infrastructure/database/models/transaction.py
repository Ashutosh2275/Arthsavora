"""
Arthsavora Transaction Relational Models
PostgreSQL source of truth for all financial movements with exact decimal precision,
integer minor units (paise), multi-source provenance, and idempotency deduplication.
"""

from datetime import date
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Date, Numeric, Boolean, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.account import Account
    from app.infrastructure.database.models.category import Category
    from app.infrastructure.database.models.user import User


class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Authoritative financial transaction record with exact numeric precision and tenant isolation."""
    __tablename__ = "transactions"
    __table_args__ = (
        # Partial unique index enforcing external transaction deduplication within each workspace
        Index(
            "uq_workspace_external_tx",
            "workspace_id",
            "external_transaction_id",
            unique=True,
            postgresql_where="external_transaction_id IS NOT NULL",
        ),
        Index("ix_transactions_workspace_date", "workspace_id", "transaction_date"),
        Index("ix_transactions_workspace_category", "workspace_id", "category_id"),
        Index("ix_transactions_workspace_status_date", "workspace_id", "status", "transaction_date"),
        Index("ix_transactions_account_date", "account_id", "transaction_date"),
        Index("ix_transactions_related_id", "related_transaction_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), default="outflow", nullable=False)  # inflow, outflow, neutral
    # Exact Fixed-Point Financial Amount (NUMERIC 18, 4) & Integer Minor Units (paise)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    settlement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="posted", nullable=False)  # pending, posted, failed, cancelled, reversed
    source_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # manual, csv_import, pdf_import, bank_feed, account_aggregator, credit_card_statement, ocr, internal_adjustment, system
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_ai_predicted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    source_provenance: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="transactions")
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    category: Mapped["Category | None"] = relationship("Category", back_populates="transactions")
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    related_transaction: Mapped["Transaction | None"] = relationship(
        "Transaction",
        foreign_keys=[related_transaction_id],
        remote_side="Transaction.id",
    )
    original_transaction: Mapped["Transaction | None"] = relationship(
        "Transaction",
        foreign_keys=[original_transaction_id],
        remote_side="Transaction.id",
    )

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.transaction_type} amount={self.amount} {self.currency} status={self.status}>"
