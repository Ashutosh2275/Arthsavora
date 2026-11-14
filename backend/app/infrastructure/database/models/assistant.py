"""
Arthsavora AI Financial Assistant Relational Models
PostgreSQL source of truth for conversational history, tool execution audits,
action confirmation drafts, and operational token/cost observability.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.infrastructure.database.models.user import User
    from app.infrastructure.database.models.workspace import Workspace


class AssistantConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Authoritative conversation thread bounded to a specific tenant workspace and user.
    Maintains model configuration, title, and conversation status.
    """
    __tablename__ = "assistant_conversations"
    __table_args__ = (
        Index("ix_assistant_conv_workspace_user", "workspace_id", "user_id"),
        Index("ix_assistant_conv_workspace_updated", "workspace_id", "updated_at"),
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

    title: Mapped[str] = mapped_column(String(255), default="New Financial Conversation", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)  # active, archived, deleted
    model_provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="mock-fin-v1", nullable=False)
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")
    messages: Mapped[List["AssistantMessage"]] = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at.asc()",
    )
    action_drafts: Mapped[List["AssistantActionDraft"]] = relationship(
        "AssistantActionDraft",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AssistantConversation id={self.id} title={self.title} status={self.status}>"


class AssistantMessage(Base, UUIDPrimaryKeyMixin):
    """
    Individual chronological message turn within a conversation thread.
    Contains verified user inputs, LLM responses, tool traces, and rich structured data.
    """
    __tablename__ = "assistant_messages"
    __table_args__ = (
        Index("ix_assistant_msg_conv_created", "conversation_id", "created_at"),
        Index("ix_assistant_msg_workspace", "workspace_id"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)  # expense_summary, overview, etc.

    # Tool Execution Traces & Structured Results
    tool_calls: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    tool_results: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    structured_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Telemetry
    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    conversation: Mapped["AssistantConversation"] = relationship(
        "AssistantConversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return f"<AssistantMessage id={self.id} role={self.role} intent={self.intent}>"


class AssistantActionDraft(Base, UUIDPrimaryKeyMixin):
    """
    Safe, reversible financial operation draft proposed by the assistant.
    Requires explicit, authenticated human confirmation before executing backend mutations.
    """
    __tablename__ = "assistant_action_drafts"
    __table_args__ = (
        Index("ix_action_draft_workspace_status", "workspace_id", "status"),
        Index("ix_action_draft_token", "confirmation_token", unique=True),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # create_budget_draft, create_goal_draft, create_recurring_draft, prepare_transaction_filter
    action_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="pending_confirmation",
        nullable=False,
    )  # pending_confirmation, confirmed, cancelled, expired, failed

    confirmation_token: Mapped[str] = mapped_column(String(100), nullable=False)
    execution_result: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["AssistantConversation"] = relationship(
        "AssistantConversation",
        back_populates="action_drafts",
    )
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<AssistantActionDraft id={self.id} type={self.action_type} status={self.status}>"


class AssistantUsageLog(Base, UUIDPrimaryKeyMixin):
    """
    Immutable audit and operational cost ledger for AI invocations.
    Records token consumption, provider performance, and error categories without logging private prompts.
    """
    __tablename__ = "assistant_usage_logs"
    __table_args__ = (
        Index("ix_assistant_usage_workspace", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.000000"), nullable=False)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AssistantUsageLog id={self.id} provider={self.model_provider} tokens={self.total_tokens}>"
