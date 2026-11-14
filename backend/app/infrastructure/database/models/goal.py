"""
Arthsavora Financial Goals Relational Models
PostgreSQL source of truth for target-based personal savings goals,
auditable contribution/withdrawal activity ledgers, and completion progress.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.transaction import Transaction
    from app.infrastructure.database.models.user import User


class FinancialGoal(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Authoritative financial goal entity defining target amounts, target dates,
    accumulated balances, and milestone statuses.
    """
    __tablename__ = "financial_goals"
    __table_args__ = (
        Index("ix_financial_goals_workspace_status", "workspace_id", "status"),
        Index("ix_financial_goals_target_date", "workspace_id", "target_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    goal_type: Mapped[str] = mapped_column(String(50), default="personal_savings", nullable=False)  # emergency_fund, education, travel, vehicle, home, debt_repayment, personal_savings, custom
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    target_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    current_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    start_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, completed, paused, archived
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high
    color: Mapped[str | None] = mapped_column(String(20), default="#6366f1", nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), default="target", nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    created_by: Mapped[Optional["User"]] = relationship("User")
    activities: Mapped[List["GoalActivity"]] = relationship(
        "GoalActivity",
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="desc(GoalActivity.created_at)",
    )

    def __repr__(self) -> str:
        return f"<FinancialGoal id={self.id} name='{self.name}' target={self.target_amount} current={self.current_amount} {self.currency}>"


class GoalActivity(Base, UUIDPrimaryKeyMixin):
    """
    Immutable ledger of contributions, withdrawals, and balance adjustments
    attributed to a financial goal.
    """
    __tablename__ = "goal_activities"
    __table_args__ = (
        Index("ix_goal_activities_goal", "goal_id", "created_at"),
        Index("ix_goal_activities_workspace", "workspace_id"),
    )

    goal_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type: Mapped[str] = mapped_column(String(30), nullable=False)  # contribution, withdrawal, reversal, transfer_in, transfer_out
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    resulting_balance_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    performed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[date] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    goal: Mapped["FinancialGoal"] = relationship("FinancialGoal", back_populates="activities")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")
    performed_by: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<GoalActivity id={self.id} goal={self.goal_id} type={self.activity_type} amount={self.amount}>"
