"""
Arthsavora Financial Account Relational Models
PostgreSQL source of truth for bank, cash, wallet, loan, and credit-card accounts,
along with immutable point-in-time balance snapshot history.
"""

from datetime import date, datetime
from decimal import Decimal
import uuid
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Account(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Financial account entity belonging to an explicit workspace."""
    __tablename__ = "accounts"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)  # cash, savings, current, salary, credit_card, loan, investment, digital_wallet, petty_cash, other
    account_subtype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    masked_identifier: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "••••4092"
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, inactive, archived, closed
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Balance values (stored in integer minor units / paise for exact financial precision)
    opening_balance_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    opening_balance_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    opening_balance_source: Mapped[str | None] = mapped_column(String(50), default="manual", nullable=True)

    current_book_balance_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    available_balance_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    provider_reported_balance_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    provider_reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outstanding_liability_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pending_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Credit card and loan-specific attributes
    credit_limit_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    statement_balance_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    minimum_due_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # e.g. 10.50%
    repayment_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # EMI amount

    # External Provider Connection References
    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_status: Mapped[str | None] = mapped_column(String(30), nullable=True)  # connected, disconnected, sync_failed, pending_auth

    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="account")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    balance_snapshots: Mapped[list["AccountBalanceSnapshot"]] = relationship(
        "AccountBalanceSnapshot",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="desc(AccountBalanceSnapshot.effective_at)",
    )

    __table_args__ = (
        Index("ix_accounts_workspace_status", "workspace_id", "status"),
        Index("ix_accounts_workspace_type", "workspace_id", "account_type"),
        UniqueConstraint("workspace_id", "provider_name", "provider_account_id", name="uq_workspace_provider_account"),
    )

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name} type={self.account_type} status={self.status}>"


class AccountBalanceSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Historical point-in-time balance snapshot for an account.
    Immutable record preserving provider feeds, reconciliations, and book balances.
    """
    __tablename__ = "account_balance_snapshots"

    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    balance_type: Mapped[str] = mapped_column(String(30), nullable=False)  # book, available, provider_reported, liability, opening
    balance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # manual, bank_feed, statement, reconciliation, system
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(String(30), default="unreconciled", nullable=False)  # unreconciled, reconciled, discrepant
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="balance_snapshots")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_balance_snapshots_account_effective", "account_id", "effective_at"),
        Index("ix_balance_snapshots_account_type_effective", "account_id", "balance_type", "effective_at"),
        Index("ix_balance_snapshots_workspace_type", "workspace_id", "balance_type"),
    )

    def __repr__(self) -> str:
        return f"<AccountBalanceSnapshot account_id={self.account_id} type={self.balance_type} amount={self.balance_amount} {self.currency}>"
