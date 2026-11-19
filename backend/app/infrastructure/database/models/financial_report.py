"""
ARTHSAVORA Financial Reporting, Tax Intelligence & Compliance Readiness Relational Models
PostgreSQL persistence for generated financial report snapshots, tax classification records,
versioned tax rules, tax estimation history, and data validation audit findings.
"""

from datetime import date, datetime
from decimal import Decimal
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class GeneratedReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit record of a generated financial report snapshot.
    Preserves exact metrics, statement lines, and formatting parameters for historical reproducibility.
    """
    __tablename__ = "generated_reports"
    __table_args__ = (
        Index("ix_reports_workspace_type", "workspace_id", "report_type"),
        Index("ix_reports_workspace_dates", "workspace_id", "start_date", "end_date"),
        Index("ix_reports_workspace_created", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    accounting_basis: Mapped[str] = mapped_column(String(20), default="cash", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    report_data_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(30), default="passed", nullable=False)
    generated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    export_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    generated_by: Mapped["User"] = relationship("User", foreign_keys=[generated_by_id])

    def __repr__(self) -> str:
        return f"<GeneratedReport id={self.id} type={self.report_type} period={self.start_date} to {self.end_date}>"


class TaxClassificationRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tax classification and compliance metadata associated with an authoritative financial transaction.
    Maintains transparency, user review status, and evidence document links.
    """
    __tablename__ = "tax_classification_records"
    __table_args__ = (
        UniqueConstraint("workspace_id", "transaction_id", name="uq_workspace_tx_tax_classification"),
        Index("ix_tax_class_workspace_year", "workspace_id", "tax_year"),
        Index("ix_tax_class_workspace_status", "workspace_id", "review_status"),
        Index("ix_tax_class_category", "workspace_id", "tax_category"),
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
    tax_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2026-2027"
    tax_category: Mapped[str] = mapped_column(String(100), nullable=False)  # section_80c, business_deductible, etc.
    tax_category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), default="unclassified", nullable=False)
    rule_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    taxable_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    deductible_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_rate_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    tax_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    gst_component: Mapped[str | None] = mapped_column(String(10), nullable=True)  # CGST, SGST, IGST
    hsn_sac_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    transaction: Mapped["Transaction"] = relationship("Transaction")
    evidence_document: Mapped["FinancialDocument"] = relationship("FinancialDocument")
    reviewed_by: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by_id])

    def __repr__(self) -> str:
        return f"<TaxClassification tx={self.transaction_id} cat={self.tax_category} status={self.review_status}>"


class TaxRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Versioned catalog of deterministic and heuristic tax classification rules.
    """
    __tablename__ = "tax_rules"
    __table_args__ = (
        UniqueConstraint("rule_code", "rule_version", name="uq_rule_code_version"),
        Index("ix_tax_rules_category", "category"),
    )

    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), default="IN", nullable=False)
    financial_year_applicability: Mapped[str] = mapped_column(String(20), default="ANY", nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    matcher_criteria_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<TaxRule {self.rule_code} v{self.rule_version}: {self.category}>"


class TaxEstimateSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Point-in-time calculation snapshot of an illustrative tax liability estimate.
    Includes explicit assumptions and missing information warnings.
    """
    __tablename__ = "tax_estimate_snapshots"
    __table_args__ = (
        Index("ix_tax_estimates_workspace_fy", "workspace_id", "financial_year"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)
    assessment_year: Mapped[str] = mapped_column(String(20), nullable=False)
    taxpayer_category: Mapped[str] = mapped_column(String(50), default="individual", nullable=False)
    regime: Mapped[str] = mapped_column(String(50), default="new_regime", nullable=False)
    gross_income_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    deductions_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    taxable_income_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    estimated_tax_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    effective_tax_rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    assumptions_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    missing_data_warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    calculated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    calculated_by: Mapped["User"] = relationship("User", foreign_keys=[calculated_by_id])

    def __repr__(self) -> str:
        return f"<TaxEstimateSnapshot id={self.id} FY={self.financial_year} regime={self.regime} tax={self.estimated_tax_paise}>"


class ReportValidationFinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Data quality and accounting consistency finding identified by report validation service.
    """
    __tablename__ = "report_validation_findings"
    __table_args__ = (
        Index("ix_validation_workspace_severity", "workspace_id", "severity"),
        Index("ix_validation_workspace_type", "workspace_id", "report_type"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)  # info, warning, critical
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    resolved_by: Mapped["User"] = relationship("User", foreign_keys=[resolved_by_id])

    def __repr__(self) -> str:
        return f"<ReportValidationFinding id={self.id} rule={self.rule_code} severity={self.severity}>"
