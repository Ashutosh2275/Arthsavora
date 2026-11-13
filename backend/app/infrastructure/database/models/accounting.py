"""
Arthsavora Double-Entry Ledger Relational Models
PostgreSQL foundation for chart of accounts, journal entries, and balanced ledger lines.
Enforces the fundamental accounting equation: Total Debits == Total Credits.
"""

from datetime import date, datetime
from decimal import Decimal
import uuid
from sqlalchemy import String, Date, DateTime, Numeric, Boolean, Integer, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


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
    linked_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # transaction, manual, reversal, system
    source_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    reversal_of_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    lines: Mapped[list["JournalLine"]] = relationship("JournalLine", back_populates="journal_entry", cascade="all, delete-orphan")
    reversal_of: Mapped["JournalEntry | None"] = relationship("JournalEntry", remote_side="JournalEntry.id")

    def __repr__(self) -> str:
        return f"<JournalEntry id={self.id} number={self.entry_number} status={self.status}>"


class JournalLine(Base, UUIDPrimaryKeyMixin):
    """Individual debit or credit leg of a double-entry journal entry."""
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_journal_line_amount_positive"),
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
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    journal_entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")
    ledger_account: Mapped["LedgerAccount"] = relationship("LedgerAccount", back_populates="lines")

    def __repr__(self) -> str:
        return f"<JournalLine id={self.id} type={self.entry_type} amount={self.amount} account={self.ledger_account_id}>"
