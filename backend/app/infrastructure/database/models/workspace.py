"""
Arthsavora Workspace & Multi-Tenancy Relational Models
PostgreSQL source of truth for workspace isolation, ownership, and role-based memberships.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Authoritative workspace entity isolating personal, household, and commercial business data."""
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # personal, family, business
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    default_currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
    )  # creating, active, suspended, archived, deletion_pending, deleted
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    members: Mapped[list["WorkspaceMember"]] = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="workspace", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} slug={self.slug} type={self.type} status={self.status}>"


class WorkspaceMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates users with workspaces under explicit roles (owner, admin, accountant, member, viewer)."""
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # owner, admin, member, viewer, accountant, approver, staff
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, invited, suspended, revoked
    invitation_token: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<WorkspaceMember workspace={self.workspace_id} user={self.user_id} role={self.role}>"
