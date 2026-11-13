"""
Arthsavora SQLAlchemy Base Model & Mixins
PostgreSQL Relational Schema Foundation with UUID primary keys and audit timestamps.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy relational models."""
    pass


class TimestampMixin:
    """Provides standard audit timestamps across all relational tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Provides soft-delete capabilities to prevent accidental physical data loss."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("FALSE"),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class UUIDPrimaryKeyMixin:
    """Standardizes primary keys to UUIDv4 / UUIDv7 across all domain models."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
