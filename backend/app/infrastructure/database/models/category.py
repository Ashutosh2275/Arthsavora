"""
Arthsavora Transaction Category Relational Models
Supports hierarchical (parent-child), system-default, and workspace-custom categories.
"""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.transaction import Transaction
    from app.infrastructure.database.models.merchant import Merchant
    from app.infrastructure.database.models.rule import ClassificationRule


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Hierarchical category structure with workspace custom and global system categories."""
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_workspace_category_slug"),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # NULL indicates universal system category
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    category_type: Mapped[str] = mapped_column(String(20), nullable=False)  # income, expense, transfer, system
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, archived
    workspace_type: Mapped[str] = mapped_column(String(30), default="all", nullable=False)  # personal, family, business, all
    transaction_type_compatibility: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    parent: Mapped[Optional["Category"]] = relationship("Category", remote_side="Category.id", back_populates="children")
    children: Mapped[List["Category"]] = relationship("Category", back_populates="parent")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name} type={self.category_type} is_system={self.is_system}>"
