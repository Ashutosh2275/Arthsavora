"""
Arthsavora Transaction Classification Rule Relational Models
Deterministic rules for transaction categorization and merchant mapping.
"""

import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.category import Category
    from app.infrastructure.database.models.merchant import Merchant
    from app.infrastructure.database.models.user import User


class ClassificationRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deterministic classification rule evaluated in priority order."""
    __tablename__ = "classification_rules"
    __table_args__ = (
        Index("ix_classification_rules_workspace_priority", "workspace_id", "priority", "is_enabled"),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # NULL indicates system-wide rule
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)  # Higher number = higher precedence
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rule_scope: Mapped[str] = mapped_column(String(20), default="workspace", nullable=False)  # system, workspace, user
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    suggested_category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    suggested_merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    suggested_category: Mapped["Category"] = relationship("Category")
    suggested_merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    created_by: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<ClassificationRule id={self.id} name={self.name} priority={self.priority} enabled={self.is_enabled}>"
