"""
Arthsavora Small Business Finance Relational Models
PostgreSQL source of truth for business profiles, clients, vendors,
invoices, line items, payments, payables, and immutable audit activities.
"""

from datetime import date, datetime, timezone
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
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class BusinessProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Business identity, statutory identifiers, fiscal settings, and tax configurations."""
    __tablename__ = "business_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_business_profile_workspace"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(String(50), default="freelancer", nullable=False)
    business_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    business_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    business_address: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="IN", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    financial_year_start_month: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tax_configuration: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    invoice_settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace")

    def __repr__(self) -> str:
        return f"<BusinessProfile workspace={self.workspace_id} name={self.business_name} type={self.business_type}>"


class BusinessClient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Client/customer record for commercial invoicing and accounts receivable tracking."""
    __tablename__ = "business_clients"
    __table_args__ = (
        Index("ix_business_clients_workspace_name", "workspace_id", "name"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_type: Mapped[str] = mapped_column(String(50), default="business", nullable=False)  # individual, business, organization
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_address: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, archived

    workspace: Mapped["Workspace"] = relationship("Workspace")
    invoices: Mapped[list["BusinessInvoice"]] = relationship("BusinessInvoice", back_populates="client")

    def __repr__(self) -> str:
        return f"<BusinessClient id={self.id} name={self.name} status={self.status}>"


class BusinessVendor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Vendor/supplier record for operating expense logging and accounts payable tracking."""
    __tablename__ = "business_vendors"
    __table_args__ = (
        Index("ix_business_vendors_workspace_name", "workspace_id", "name"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_type: Mapped[str] = mapped_column(String(50), default="service_provider", nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    payables: Mapped[list["BusinessPayable"]] = relationship("BusinessPayable", back_populates="vendor")

    def __repr__(self) -> str:
        return f"<BusinessVendor id={self.id} name={self.name} status={self.status}>"


class BusinessInvoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authoritative commercial invoice header for client receivables and revenue tracking."""
    __tablename__ = "business_invoices"
    __table_args__ = (
        UniqueConstraint("workspace_id", "invoice_number", name="uq_business_invoice_number"),
        CheckConstraint("subtotal_amount_paise >= 0", name="chk_invoice_subtotal_paise_nonneg"),
        CheckConstraint("discount_amount_paise >= 0", name="chk_invoice_discount_paise_nonneg"),
        CheckConstraint("tax_amount_paise >= 0", name="chk_invoice_tax_paise_nonneg"),
        CheckConstraint("total_amount_paise >= 0", name="chk_invoice_total_paise_nonneg"),
        CheckConstraint("paid_amount_paise >= 0", name="chk_invoice_paid_paise_nonneg"),
        CheckConstraint("status IN ('draft', 'issued', 'partially_paid', 'paid', 'overdue', 'cancelled')", name="chk_invoice_status"),
        Index("ix_business_invoices_workspace_dates", "workspace_id", "invoice_date", "due_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("business_clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    subtotal_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    payment_instructions: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issued_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    client: Mapped["BusinessClient"] = relationship("BusinessClient", back_populates="invoices")
    line_items: Mapped[list["BusinessInvoiceLineItem"]] = relationship(
        "BusinessInvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="BusinessInvoiceLineItem.line_order",
    )
    payments: Mapped[list["BusinessInvoicePayment"]] = relationship(
        "BusinessInvoicePayment",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    journal_entry: Mapped["JournalEntry | None"] = relationship("JournalEntry")

    def __repr__(self) -> str:
        return f"<BusinessInvoice number={self.invoice_number} status={self.status} total={self.total_amount_paise}>"


class BusinessInvoiceLineItem(Base, UUIDPrimaryKeyMixin):
    """Detailed itemized line entry within a business invoice."""
    __tablename__ = "business_invoice_line_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_invoice_line_quantity_pos"),
        CheckConstraint("unit_price_paise >= 0", name="chk_invoice_line_price_nonneg"),
        CheckConstraint("discount_paise >= 0", name="chk_invoice_line_discount_nonneg"),
        CheckConstraint("tax_amount_paise >= 0", name="chk_invoice_line_tax_nonneg"),
        CheckConstraint("total_amount_paise >= 0", name="chk_invoice_line_total_nonneg"),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("business_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    hsn_sac_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("1.0"), nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.0"), nullable=False)
    cgst_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.0"), nullable=False)
    sgst_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.0"), nullable=False)
    igst_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.0"), nullable=False)
    tax_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    invoice: Mapped["BusinessInvoice"] = relationship("BusinessInvoice", back_populates="line_items")

    def __repr__(self) -> str:
        return f"<BusinessInvoiceLineItem desc='{self.description}' total={self.total_amount_paise}>"


class BusinessInvoicePayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Recorded payment allocation against an issued business invoice."""
    __tablename__ = "business_invoice_payments"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="chk_invoice_payment_amount_pos"),
        Index("ix_business_invoice_payments_invoice_date", "invoice_id", "payment_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("business_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), default="bank_transfer", nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    financial_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    invoice: Mapped["BusinessInvoice"] = relationship("BusinessInvoice", back_populates="payments")
    financial_account: Mapped["Account | None"] = relationship("Account")
    journal_entry: Mapped["JournalEntry | None"] = relationship("JournalEntry")

    def __repr__(self) -> str:
        return f"<BusinessInvoicePayment invoice={self.invoice_id} amount={self.amount_paise}>"


class BusinessPayable(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Vendor bills and operational obligations tracked for Accounts Payable (AP)."""
    __tablename__ = "business_payables"
    __table_args__ = (
        CheckConstraint("subtotal_amount_paise >= 0", name="chk_payable_subtotal_paise_nonneg"),
        CheckConstraint("tax_amount_paise >= 0", name="chk_payable_tax_paise_nonneg"),
        CheckConstraint("total_amount_paise >= 0", name="chk_payable_total_paise_nonneg"),
        CheckConstraint("paid_amount_paise >= 0", name="chk_payable_paid_paise_nonneg"),
        CheckConstraint("status IN ('draft', 'recorded', 'due', 'partially_paid', 'paid', 'overdue', 'cancelled')", name="chk_payable_status"),
        Index("ix_business_payables_workspace_dates", "workspace_id", "bill_date", "due_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("business_vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bill_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    subtotal_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    vendor: Mapped["BusinessVendor"] = relationship("BusinessVendor", back_populates="payables")
    payments: Mapped[list["BusinessPayablePayment"]] = relationship(
        "BusinessPayablePayment",
        back_populates="payable",
        cascade="all, delete-orphan",
    )
    journal_entry: Mapped["JournalEntry | None"] = relationship("JournalEntry")

    def __repr__(self) -> str:
        return f"<BusinessPayable id={self.id} vendor={self.vendor_id} total={self.total_amount_paise} status={self.status}>"


class BusinessPayablePayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Payment recorded against a vendor bill / business payable."""
    __tablename__ = "business_payable_payments"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="chk_payable_payment_amount_pos"),
        Index("ix_business_payable_payments_date", "payable_id", "payment_date"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payable_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("business_payables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), default="bank_transfer", nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    financial_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    payable: Mapped["BusinessPayable"] = relationship("BusinessPayable", back_populates="payments")
    financial_account: Mapped["Account | None"] = relationship("Account")
    journal_entry: Mapped["JournalEntry | None"] = relationship("JournalEntry")

    def __repr__(self) -> str:
        return f"<BusinessPayablePayment payable={self.payable_id} amount={self.amount_paise}>"


class BusinessActivity(Base, UUIDPrimaryKeyMixin):
    """Immutable audit timeline of business finance and commercial operations."""
    __tablename__ = "business_activities"
    __table_args__ = (
        Index("ix_business_activities_workspace_created", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    actor: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<BusinessActivity type={self.activity_type} at={self.created_at}>"
