"""
Arthsavora Financial Account Relational Models
PostgreSQL source of truth for bank, cash, wallet, loan, and credit-card accounts.
"""

from datetime import date
import uuid
from sqlalchemy import String, Date, ForeignKey
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
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)  # cash, bank, savings, current, credit_card, loan, investment, wallet, other
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    masked_identifier: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "XX4092"
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, frozen, closed
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="account")

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name} type={self.account_type} status={self.status}>"
