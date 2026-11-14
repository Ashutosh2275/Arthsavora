"""
Arthsavora Recurring Transactions, Subscriptions & Cash-Flow Commitments Models
PostgreSQL source of truth for recurring definitions, expected occurrences,
subscriptions, idempotent reminders, and detected pattern suggestions.
"""

from datetime import date, datetime
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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.account import Account
    from app.infrastructure.database.models.category import Category
    from app.infrastructure.database.models.merchant import Merchant
    from app.infrastructure.database.models.transaction import Transaction
    from app.infrastructure.database.models.user import User


class RecurringDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Authoritative definition of a recurring financial activity (e.g. rent, salary, EMI, utility).
    Represents an EXPECTATION of future financial events, not an actual completed transaction.
    """
    __tablename__ = "recurring_definitions"
    __table_args__ = (
        Index("ix_recurring_defs_ws_status", "workspace_id", "status"),
        Index("ix_recurring_defs_ws_next_date", "workspace_id", "next_expected_date"),
        Index("ix_recurring_defs_ws_category", "workspace_id", "category_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    direction: Mapped[str] = mapped_column(String(10), default="outflow", nullable=False)  # inflow, outflow
    transaction_type: Mapped[str] = mapped_column(String(50), default="expense", nullable=False)  # income, expense, transfer

    # Monetary limits
    expected_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    is_variable_amount: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # Classifications & Accounts
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    merchant_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Recurrence rules
    frequency: Mapped[str] = mapped_column(String(30), default="monthly", nullable=False)  # daily, weekly, biweekly, monthly, quarterly, semi_annual, annual, custom
    interval: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-31
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-6
    end_of_month_policy: Mapped[str] = mapped_column(String(30), default="last_day", nullable=False)

    # Lifecycle & schedule dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_expected_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, paused, cancelled, completed

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    category: Mapped[Optional["Category"]] = relationship("Category")
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    account: Mapped[Optional["Account"]] = relationship("Account")
    created_by: Mapped[Optional["User"]] = relationship("User")
    occurrences: Mapped[List["RecurringOccurrence"]] = relationship(
        "RecurringOccurrence",
        back_populates="recurring_definition",
        cascade="all, delete-orphan",
        order_by="RecurringOccurrence.expected_date.asc()",
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        back_populates="recurring_definition",
    )
    reminders: Mapped[List["RecurringReminder"]] = relationship(
        "RecurringReminder",
        back_populates="recurring_definition",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RecurringDefinition id={self.id} name='{self.name}' freq={self.frequency} amount={self.expected_amount} {self.currency}>"


class RecurringOccurrence(Base, UUIDPrimaryKeyMixin):
    """
    Individual scheduled instance of an expected recurring financial event.
    Guarantees strict separation from actual transactions. An occurrence is only
    associated with an actual transaction when verified and matched.
    """
    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        UniqueConstraint("recurring_definition_id", "expected_date", name="uq_recurring_occurrence_schedule"),
        Index("ix_occurrences_ws_status_date", "workspace_id", "status", "expected_date"),
        Index("ix_occurrences_ws_expected_date", "workspace_id", "expected_date"),
        Index("ix_occurrences_matched_tx", "matched_transaction_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recurring_definition_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recurring_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expected_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    expected_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # Status: scheduled, upcoming, due, matched, confirmed, skipped, cancelled, overdue
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False)

    # Reconciliation link to actual transaction (optional and strictly post-facto)
    matched_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    matched_amount_paise: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    amount_variance_paise: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    match_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    recurring_definition: Mapped["RecurringDefinition"] = relationship(
        "RecurringDefinition",
        back_populates="occurrences",
    )
    matched_transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")
    reminders: Mapped[List["RecurringReminder"]] = relationship(
        "RecurringReminder",
        back_populates="occurrence",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RecurringOccurrence id={self.id} date={self.expected_date} status={self.status} amt={self.expected_amount}>"


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Dedicated subscription management record for digital services, memberships, and SaaS.
    Tracks trial periods, renewal cycles, cancellation deadlines, and estimated monthly costs.
    """
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_ws_status", "workspace_id", "status"),
        Index("ix_subscriptions_ws_next_billing", "workspace_id", "next_billing_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recurring_definition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recurring_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    expected_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    billing_frequency: Mapped[str] = mapped_column(String(30), default="monthly", nullable=False)  # weekly, monthly, quarterly, semi_annual, annual
    billing_cycle_interval: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_billing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    renewal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    trial_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cancellation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Strictly non-sensitive display label (e.g. "HDFC Visa ending 4092"). Never card numbers or PINs.
    payment_method_display: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status: active, trial, paused, cancelled, expired, unknown
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    is_variable_pricing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    recurring_definition: Mapped[Optional["RecurringDefinition"]] = relationship(
        "RecurringDefinition",
        back_populates="subscriptions",
    )
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    category: Mapped[Optional["Category"]] = relationship("Category")
    account: Mapped[Optional["Account"]] = relationship("Account")
    reminders: Mapped[List["RecurringReminder"]] = relationship(
        "RecurringReminder",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} name='{self.name}' status={self.status} amt={self.expected_amount} {self.currency}>"


class RecurringReminder(Base, UUIDPrimaryKeyMixin):
    """
    Idempotent notification reminder record for upcoming payments, renewals, trial expirations, and overdue items.
    """
    __tablename__ = "recurring_reminders"
    __table_args__ = (
        Index("ix_reminders_ws_read", "workspace_id", "is_read"),
        Index("ix_reminders_ws_scheduled", "workspace_id", "scheduled_for"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    occurrence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recurring_occurrences.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    recurring_definition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recurring_definitions.id", ondelete="CASCADE"),
        nullable=True,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Type: upcoming_payment, upcoming_renewal, trial_ending, payment_overdue, cancellation_deadline
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False)
    days_before: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)
    notification_channel: Mapped[str] = mapped_column(String(30), default="in_app", nullable=False)

    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    occurrence: Mapped[Optional["RecurringOccurrence"]] = relationship(
        "RecurringOccurrence",
        back_populates="reminders",
    )
    recurring_definition: Mapped[Optional["RecurringDefinition"]] = relationship(
        "RecurringDefinition",
        back_populates="reminders",
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="reminders",
    )

    def __repr__(self) -> str:
        return f"<RecurringReminder id={self.id} type={self.reminder_type} scheduled={self.scheduled_for} sent={self.is_sent}>"


class RecurringSuggestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Detected recurring pattern candidate identified by the transaction intelligence engine.
    Requires explicit user confirmation before creating an authoritative recurring definition.
    """
    __tablename__ = "recurring_suggestions"
    __table_args__ = (
        Index("ix_suggestions_ws_status", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_description: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), default="outflow", nullable=False)

    suggested_frequency: Mapped[str] = mapped_column(String(30), default="monthly", nullable=False)
    suggested_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    suggested_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    min_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    first_seen_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_seen_date: Mapped[date] = mapped_column(Date, nullable=False)
    estimated_next_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, confirmed, dismissed
    dismissed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    category: Mapped[Optional["Category"]] = relationship("Category")

    def __repr__(self) -> str:
        return f"<RecurringSuggestion id={self.id} merchant='{self.merchant_name}' conf={self.confidence_score} status={self.status}>"
