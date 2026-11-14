"""
Arthsavora Family Finance Relational Models
PostgreSQL source of truth for household profiles, shared expense allocations,
member contributions, settlement tracking, and personal account sharing.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
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
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.account import Account
    from app.infrastructure.database.models.transaction import Transaction
    from app.infrastructure.database.models.user import User


class FamilyProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Authoritative profile configuration for a collaborative family workspace.
    Enforces household name, base currency, timezone, and allocation defaults.
    """
    __tablename__ = "family_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_family_profile_workspace"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household_name: Mapped[str] = mapped_column(String(255), nullable=False)
    household_currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    household_timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    monthly_budget_start_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    default_allocation_method: Mapped[str] = mapped_column(String(30), default="equal", nullable=False)
    contribution_reminder_day: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    enable_shared_budget_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_contribution_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace")

    def __repr__(self) -> str:
        return f"<FamilyProfile household={self.household_name} ws={self.workspace_id}>"


class FamilyExpenseAllocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Accounting allocation record dividing a shared family expense among members.
    Sum of allocation item shares must equal total_amount_paise exactly.
    """
    __tablename__ = "family_expense_allocations"
    __table_args__ = (
        Index("ix_family_allocations_ws_tx", "workspace_id", "transaction_id"),
        Index("ix_family_allocations_ws_status", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allocation_method: Mapped[str] = mapped_column(String(30), default="equal", nullable=False)  # equal, fixed, percentage, custom
    total_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, revised, cancelled
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    transaction: Mapped["Transaction"] = relationship("Transaction")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    items: Mapped[list["FamilyExpenseAllocationItem"]] = relationship(
        "FamilyExpenseAllocationItem",
        back_populates="allocation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<FamilyExpenseAllocation id={self.id} tx={self.transaction_id} method={self.allocation_method}>"


class FamilyExpenseAllocationItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual member share within an expense allocation.
    Guaranteed non-negative integer paise.
    """
    __tablename__ = "family_expense_allocation_items"
    __table_args__ = (
        Index("ix_allocation_items_allocation_id", "allocation_id"),
        Index("ix_allocation_items_member", "member_user_id"),
        CheckConstraint("assigned_share_paise >= 0", name="chk_positive_share_paise"),
    )

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("family_expense_allocations.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_share_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_paid_by: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settlement_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, settled, waived
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    allocation: Mapped["FamilyExpenseAllocation"] = relationship("FamilyExpenseAllocation", back_populates="items")
    member: Mapped["User"] = relationship("User", foreign_keys=[member_user_id])

    def __repr__(self) -> str:
        return f"<AllocationItem member={self.member_user_id} share={self.assigned_share_paise} paise>"


class FamilyMemberContribution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks expected and recorded member contributions into the household pool.
    Distinguishes scheduled expectation from actual recorded payments.
    """
    __tablename__ = "family_member_contributions"
    __table_args__ = (
        Index("ix_family_contributions_ws_period", "workspace_id", "period"),
        Index("ix_family_contributions_ws_member", "workspace_id", "member_user_id"),
        Index("ix_family_contributions_status", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "2026-11"
    contribution_type: Mapped[str] = mapped_column(String(30), default="monthly", nullable=False)  # monthly, fixed, percentage, one_time, voluntary
    expected_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    paid_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="expected", nullable=False)  # expected, partially_paid, paid, overdue, waived, cancelled
    recorded_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    member: Mapped["User"] = relationship("User", foreign_keys=[member_user_id])
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    recorded_transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")

    def __repr__(self) -> str:
        return f"<FamilyMemberContribution member={self.member_user_id} period={self.period} status={self.status}>"


class FamilyAccountShare(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Explicit authorization bridge allowing a member to share a personal account into family workspace.
    Enforces privacy boundaries: personal transactions remain hidden when share_scope is balance_only.
    """
    __tablename__ = "family_account_shares"
    __table_args__ = (
        UniqueConstraint("family_workspace_id", "account_id", name="uq_family_shared_account"),
        Index("ix_family_shares_ws", "family_workspace_id", "is_active"),
    )

    family_workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_scope: Mapped[str] = mapped_column(String(30), default="balance_only", nullable=False)  # balance_only, summary_only, full_visibility
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    family_workspace: Mapped["Workspace"] = relationship("Workspace")
    account: Mapped["Account"] = relationship("Account")
    shared_by: Mapped["User"] = relationship("User", foreign_keys=[shared_by_user_id])

    def __repr__(self) -> str:
        return f"<FamilyAccountShare ws={self.family_workspace_id} account={self.account_id} scope={self.share_scope}>"


class FamilyActivity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit timeline for family finance workspace activities.
    Scoped strictly to the family workspace; excludes private member actions.
    """
    __tablename__ = "family_activities"
    __table_args__ = (
        Index("ix_family_activities_ws_time", "workspace_id", "created_at"),
        Index("ix_family_activities_type", "workspace_id", "activity_type"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # FamilyActivityType enum values
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # allocation, contribution, budget, goal, member, account
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_user_id])

    def __repr__(self) -> str:
        return f"<FamilyActivity ws={self.workspace_id} type={self.activity_type} title={self.title}>"
