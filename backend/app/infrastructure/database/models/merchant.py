"""
Arthsavora Merchant Intelligence Relational Models
PostgreSQL source of truth for recognized merchants, aliases, and category mappings.
"""

from decimal import Decimal
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.category import Category


class Merchant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Recognized commercial merchant entity with default category mapping and verification status."""
    __tablename__ = "merchants"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_workspace_merchant_slug"),
        Index("ix_merchants_workspace_name", "workspace_id", "canonical_name"),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # NULL indicates universal system merchant
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    default_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    merchant_type: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, archived
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    default_category: Mapped[Optional["Category"]] = relationship("Category")
    aliases: Mapped[List["MerchantAlias"]] = relationship("MerchantAlias", back_populates="merchant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Merchant id={self.id} name={self.canonical_name} type={self.merchant_type}>"


class MerchantAlias(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Known statement string pattern or alias mapping to a canonical merchant."""
    __tablename__ = "merchant_aliases"
    __table_args__ = (
        Index("ix_merchant_aliases_normalized", "normalized_alias"),
        UniqueConstraint("merchant_id", "alias", name="uq_merchant_alias"),
    )

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), default="exact", nullable=False)  # exact, prefix, contains, regex
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.0000"), nullable=False)

    # Relationship
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="aliases")

    def __repr__(self) -> str:
        return f"<MerchantAlias id={self.id} alias={self.alias} normalized={self.normalized_alias}>"
