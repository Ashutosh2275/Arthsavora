"""
Arthsavora Append-Oriented Audit Log Relational Models
PostgreSQL source of truth for immutable action logging, correlation tracing, and user attribution.
Attribution survives workspace member revocations.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable audit entry capturing actor, workspace, action, entity, and correlation ID."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_workspace_timestamp", "workspace_id", "timestamp"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, POST_JOURNAL, REVERSE_JOURNAL
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # transaction, journal_entry, account, workspace
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # X-Request-ID
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Sanitized of secrets
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Sanitized of secrets
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} entity={self.entity_type} actor={self.actor_id}>"
