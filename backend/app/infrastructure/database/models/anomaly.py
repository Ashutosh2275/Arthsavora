"""
Arthsavora Financial Anomaly Detection, Fraud Signals & Risk Intelligence Models
PostgreSQL source of truth for detected anomalies, user review ledgers,
configurable detection rules, and user-approved whitelist exceptions.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
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

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.transaction import Transaction
    from app.infrastructure.database.models.account import Account
    from app.infrastructure.database.models.merchant import Merchant
    from app.infrastructure.database.models.category import Category
    from app.infrastructure.database.models.user import User


class AnomalyDetection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Financial anomaly detection event representing suspicious, unusual, or unexpected
    patterns in transactions, recurring commitments, account balances, or statements.
    Informational/advisory only: never mutates ledgers or blocks payments.
    """
    __tablename__ = "anomaly_detections"
    __table_args__ = (
        Index("ix_anomaly_detections_ws_status", "workspace_id", "status"),
        Index("ix_anomaly_detections_ws_severity", "workspace_id", "severity"),
        Index("ix_anomaly_detections_ws_detected", "workspace_id", "detected_at"),
        Index("ix_anomaly_detections_tx", "transaction_id"),
        Index("ix_anomaly_detections_account", "account_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Classification
    detection_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # amount_outlier, frequency_burst, merchant_novelty, category_spike, recurring_increase, cancelled_recurring_charge, balance_discrepancy, duplicate_candidate, ml_outlier
    detection_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # deterministic_rule, statistical_mad, statistical_iqr, ml_isolation_forest, deduplication_engine
    severity: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
    )  # informational, low, medium, high, critical
    risk_score: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
    )  # 0 to 100
    status: Mapped[str] = mapped_column(
        String(30),
        default="new",
        nullable=False,
    )  # new, under_review, acknowledged, expected_activity, dismissed, escalated

    # Explainability & Evidence
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    rule_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0.0", nullable=False)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")
    account: Mapped[Optional["Account"]] = relationship("Account")
    resolved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by_id])
    reviews: Mapped[List["AnomalyReview"]] = relationship(
        "AnomalyReview",
        back_populates="anomaly",
        cascade="all, delete-orphan",
        order_by="AnomalyReview.created_at.desc()",
    )


class AnomalyReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable review event recording human actions, confirmations, escalations,
    dismissals, and exceptions created in response to detected anomalies.
    """
    __tablename__ = "anomaly_reviews"
    __table_args__ = (
        Index("ix_anomaly_reviews_anomaly", "anomaly_id"),
        Index("ix_anomaly_reviews_ws", "workspace_id", "created_at"),
    )

    anomaly_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("anomaly_detections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # acknowledge, mark_expected, mark_suspicious, dismiss, escalate, reopen, create_exception
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    anomaly: Mapped["AnomalyDetection"] = relationship("AnomalyDetection", back_populates="reviews")
    reviewer: Mapped[Optional["User"]] = relationship("User")


class DetectionRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Configurable deterministic anomaly detection rule with adjustable thresholds.
    Can be a system global default (workspace_id IS NULL) or workspace custom override.
    """
    __tablename__ = "detection_rules"
    __table_args__ = (
        Index("ix_detection_rules_ws_code", "workspace_id", "rule_code"),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detection_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # amount, frequency, merchant, category, timing, account, recurring, duplicate, import
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    threshold_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)

    # Relationships
    workspace: Mapped[Optional["Workspace"]] = relationship("Workspace")


class DetectionException(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User-confirmed detection exception (whitelist) suppressing alerts for specific
    merchants, categories, accounts, or amount ceilings (e.g., annual tuition or known contractor).
    """
    __tablename__ = "detection_exceptions"
    __table_args__ = (
        Index("ix_detection_exceptions_ws", "workspace_id"),
        Index("ix_detection_exceptions_merchant", "workspace_id", "merchant_id"),
        Index("ix_detection_exceptions_category", "workspace_id", "category_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    merchant_name_pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    category: Mapped[Optional["Category"]] = relationship("Category")
    account: Mapped[Optional["Account"]] = relationship("Account")
    created_by: Mapped[Optional["User"]] = relationship("User")
