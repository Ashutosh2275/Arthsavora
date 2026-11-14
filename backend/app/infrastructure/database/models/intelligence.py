"""
Arthsavora Transaction Classification & Feedback Relational Models
Stores prediction outputs, confidence scores, explainability metadata, and user corrections.
"""

from decimal import Decimal
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.category import Category
    from app.infrastructure.database.models.merchant import Merchant
    from app.infrastructure.database.models.rule import ClassificationRule
    from app.infrastructure.database.models.transaction import Transaction
    from app.infrastructure.database.models.user import User


class TransactionClassification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Categorization suggestion with confidence score, method, and explanation."""
    __tablename__ = "transaction_classifications"
    __table_args__ = (
        Index("ix_tx_classifications_workspace", "workspace_id"),
        Index("ix_tx_classifications_tx", "transaction_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suggested_category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    suggested_merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    suggested_merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(20), nullable=False)  # high, medium, low, unknown
    method: Mapped[str] = mapped_column(String(50), nullable=False)  # system_rule, user_rule, merchant_alias, ml_model, manual
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("classification_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0.0", nullable=False)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="suggested", nullable=False)  # suggested, accepted, rejected, corrected

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction")
    suggested_category: Mapped["Category"] = relationship("Category")
    suggested_merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    rule: Mapped[Optional["ClassificationRule"]] = relationship("ClassificationRule")


class UserClassificationFeedback(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User feedback and corrections for continuous improvement and rule creation."""
    __tablename__ = "user_classification_feedback"
    __table_args__ = (
        Index("ix_user_feedback_workspace", "workspace_id"),
        Index("ix_user_feedback_tx", "transaction_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    classification_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transaction_classifications.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confirmed_merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_method: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    feedback_action: Mapped[str] = mapped_column(String(30), nullable=False)  # accept, correct_category, correct_merchant, mark_unknown, create_rule
    feedback_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("classification_rules.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction")
    confirmed_category: Mapped["Category"] = relationship("Category", foreign_keys=[confirmed_category_id])
    created_rule: Mapped[Optional["ClassificationRule"]] = relationship("ClassificationRule")
