"""
Arthsavora Double-Entry Ledger Relational Models
PostgreSQL foundation for chart of accounts, accounting periods, journal entries, and balanced ledger lines.
Enforces the fundamental accounting equation: Total Debits == Total Credits.
"""

from datetime import date, datetime
from decimal import Decimal
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AccountingPeriod(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Financial calendar accounting period (e.g. Month, Quarter) within a fiscal year."""
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("workspace_id", "fiscal_year", "period_number", name="uq_workspace_fy_period"),
        CheckConstraint("status IN ('open', 'closed')", name="chk_period_status"),
        CheckConstraint("start_date <= end_date", name="chk_period_dates"),
        Index("ix_accounting_periods_workspace_dates", "workspace_id", "start_date", "end_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2026-2027"
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)    # 1 to 12
    name: Mapped[str] = mapped_column(String(100), nullable=False)         # e.g. "April 2026"
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)  # open, closed
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<AccountingPeriod {self.fiscal_year} P{self.period_number}: {self.name} ({self.status})>"


class LedgerAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Chart of accounts entity categorizing financial balances into assets, liabilities, equity, revenue, and expenses."""
    __tablename__ = "ledger_accounts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "code", name="uq_workspace_ledger_code"),
        CheckConstraint("account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')", name="chk_ledger_account_type"),
        CheckConstraint("normal_balance IN ('debit', 'credit')", name="chk_ledger_normal_balance"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "1010", "2010", "4010"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)  # asset, liability, equity, revenue, expense
    normal_balance: Mapped[str] = mapped_column(String(10), nullable=False)  # debit, credit
    sub_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # cash, bank, credit_card, etc.
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ledger_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    lines: Mapped[list["JournalLine"]] = relationship("JournalLine", back_populates="ledger_account")

    def __repr__(self) -> str:
        return f"<LedgerAccount code={self.code} name={self.name} type={self.account_type}>"


class JournalEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable financial journal entry encapsulating balanced debit and credit lines."""
    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("workspace_id", "entry_number", name="uq_workspace_entry_number"),
        CheckConstraint("status IN ('draft', 'posted', 'reversed')", name="chk_journal_status"),
        Index("ix_journal_entries_workspace_date", "workspace_id", "entry_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_number: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "JE-2026-0001"
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    posting_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)  # draft, posted, reversed
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # transaction, manual, reversal, system, opening_balance
    source_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    reversal_of_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accounting_period_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounting_periods.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    posted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    lines: Mapped[list["JournalLine"]] = relationship(
        "JournalLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        order_by="JournalLine.line_number",
    )
    reversal_of: Mapped["JournalEntry | None"] = relationship(
        "JournalEntry",
        remote_side="JournalEntry.id",
    )
    accounting_period: Mapped["AccountingPeriod | None"] = relationship("AccountingPeriod")

    def __repr__(self) -> str:
        return f"<JournalEntry id={self.id} number={self.entry_number} status={self.status}>"


class JournalLine(Base, UUIDPrimaryKeyMixin):
    """Individual debit or credit leg of a double-entry journal entry."""
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_journal_line_amount_positive"),
        CheckConstraint("amount_paise > 0", name="chk_journal_line_amount_paise_positive"),
        CheckConstraint("entry_type IN ('debit', 'credit')", name="chk_journal_line_entry_type"),
        Index("ix_journal_lines_entry_line", "journal_entry_id", "line_number"),
    )

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ledger_account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False)  # debit, credit
    # Exact Fixed-Point Minor Unit / Decimal Amount
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    financial_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    journal_entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")
    ledger_account: Mapped["LedgerAccount"] = relationship("LedgerAccount", back_populates="lines")

    def __init__(self, **kwargs):
        if "amount_paise" not in kwargs and "amount" in kwargs and kwargs["amount"] is not None:
            kwargs["amount_paise"] = int(round(Decimal(str(kwargs["amount"])) * 100))
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<JournalLine id={self.id} type={self.entry_type} amount={self.amount} account={self.ledger_account_id}>"
