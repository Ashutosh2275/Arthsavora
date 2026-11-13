"""
Arthsavora Transaction Category Relational Models
Supports hierarchical (parent-child), system-default, and workspace-custom categories.
"""

import uuid
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


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
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, archived

    # Relationships
    parent: Mapped["Category | None"] = relationship("Category", remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship("Category", back_populates="parent")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name} type={self.category_type} is_system={self.is_system}>"
