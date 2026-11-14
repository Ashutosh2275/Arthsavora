"""
Arthsavora Budgeting Relational Models
PostgreSQL source of truth for monthly, custom, category, and overall budgets,
along with category spending allocations, historical revision audits, and idempotent threshold alerts.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.category import Category
    from app.infrastructure.database.models.user import User


class Budget(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Authoritative budget entity defining overall limits, period boundaries,
    and recurrence configurations for an explicit workspace.
    """
    __tablename__ = "budgets"
    __table_args__ = (
        Index("ix_budgets_workspace_period", "workspace_id", "start_date", "end_date"),
        Index("ix_budgets_workspace_status", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_type: Mapped[str] = mapped_column(String(50), default="monthly", nullable=False)  # monthly, category, overall, custom, annual
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Total overall allocation in minor units (paise) and major units
    total_allocated_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_allocated: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    recurrence_interval: Mapped[str] = mapped_column(String(30), default="monthly", nullable=False)  # monthly, quarterly, annual, none
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, paused, archived, closed
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    created_by: Mapped[Optional["User"]] = relationship("User")
    allocations: Mapped[List["BudgetAllocation"]] = relationship(
        "BudgetAllocation",
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="BudgetAllocation.allocated_amount_paise.desc()",
    )
    revisions: Mapped[List["BudgetRevision"]] = relationship(
        "BudgetRevision",
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="desc(BudgetRevision.created_at)",
    )
    alerts: Mapped[List["BudgetAlert"]] = relationship(
        "BudgetAlert",
        back_populates="budget",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Budget id={self.id} name='{self.name}' type={self.budget_type} allocated={self.total_allocated} {self.currency}>"


class BudgetAllocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Specific spending allocation assigned to an individual category within a budget.
    Guarantees unique category allocation per budget via partial/unique constraints.
    """
    __tablename__ = "budget_allocations"
    __table_args__ = (
        UniqueConstraint("budget_id", "category_id", name="uq_budget_category_allocation"),
        Index("ix_budget_allocations_workspace", "workspace_id"),
        Index("ix_budget_allocations_category", "category_id"),
    )

    budget_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    allocated_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    warning_threshold_percentage: Mapped[int] = mapped_column(Integer, default=80, nullable=False)  # 50, 75, 80, 90, 100
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, inactive
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    budget: Mapped["Budget"] = relationship("Budget", back_populates="allocations")
    category: Mapped["Category"] = relationship("Category")

    def __repr__(self) -> str:
        return f"<BudgetAllocation id={self.id} budget={self.budget_id} category={self.category_id} amount={self.allocated_amount}>"


class BudgetRevision(Base, UUIDPrimaryKeyMixin):
    """
    Immutable audit history tracking all meaningful modifications to budget parameters,
    overall spending caps, or individual category allocations.
    """
    __tablename__ = "budget_revisions"
    __table_args__ = (
        Index("ix_budget_revisions_budget", "budget_id", "created_at"),
    )

    budget_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("budget_allocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    revision_type: Mapped[str] = mapped_column(String(50), nullable=False)  # budget_update, allocation_created, allocation_updated, allocation_removed
    previous_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    new_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[date] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    budget: Mapped["Budget"] = relationship("Budget", back_populates="revisions")
    changed_by: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<BudgetRevision id={self.id} budget={self.budget_id} type={self.revision_type}>"


class BudgetAlert(Base, UUIDPrimaryKeyMixin):
    """
    Idempotent threshold crossing alert history preventing duplicate notifications
    when a budget or category nears or exceeds its configured limits.
    """
    __tablename__ = "budget_alerts"
    __table_args__ = (
        UniqueConstraint("budget_id", "allocation_id", "threshold_percentage", name="uq_budget_alert_threshold"),
        Index("ix_budget_alerts_workspace_status", "workspace_id", "is_read"),
    )

    budget_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("budget_allocations.id", ondelete="CASCADE"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # threshold_crossed, budget_exhausted, budget_exceeded
    threshold_percentage: Mapped[int] = mapped_column(Integer, nullable=False)  # 50, 75, 80, 90, 100
    actual_spent_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allocated_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    utilization_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(20), default="in_app", nullable=False)
    created_at: Mapped[date] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    budget: Mapped["Budget"] = relationship("Budget", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<BudgetAlert id={self.id} budget={self.budget_id} threshold={self.threshold_percentage}%>"
