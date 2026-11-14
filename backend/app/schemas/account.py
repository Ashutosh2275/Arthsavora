"""
Arthsavora Financial Account Schemas
Request and response models for multi-tenant financial account management,
balance architectures, lifecycle transitions, and historical balance snapshots.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountTypeEnum(str, Enum):
    """Supported financial account types across Personal, Family, and Business workspaces."""
    # Personal & Family
    CASH = "cash"
    SAVINGS = "savings"
    CURRENT = "current"
    SALARY = "salary"
    FIXED_DEPOSIT = "fixed_deposit"
    RECURRING_DEPOSIT = "recurring_deposit"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    INVESTMENT = "investment"
    DIGITAL_WALLET = "digital_wallet"
    OTHER = "other"

    # Business
    BUSINESS_CASH = "business_cash"
    BUSINESS_BANK = "business_bank"
    BUSINESS_CURRENT = "business_current"
    BUSINESS_CREDIT_CARD = "business_credit_card"
    PETTY_CASH = "petty_cash"
    LOAN_ACCOUNT = "loan_account"
    OTHER_BUSINESS = "other_business"


class AccountStatusEnum(str, Enum):
    """Controlled account lifecycle statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    CLOSED = "closed"


class BalanceTypeEnum(str, Enum):
    """Categorized balance measurement types."""
    BOOK = "book"
    AVAILABLE = "available"
    PROVIDER_REPORTED = "provider_reported"
    LIABILITY = "liability"
    OPENING = "opening"


# ---------------------------------------------------------------------------
# Balance DTOs
# ---------------------------------------------------------------------------


class BalanceBreakdown(BaseModel):
    """Comprehensive, unambiguous balance representation with explicit sources."""
    currency: str = "INR"
    book_balance: str = Field("0.00", description="Derivation from posted transactions and journals")
    book_balance_paise: int = 0
    available_balance: Optional[str] = Field(None, description="Reported available funds or calculation")
    available_balance_paise: Optional[int] = None
    provider_reported_balance: Optional[str] = Field(None, description="Balance reported by external provider feed")
    provider_reported_balance_paise: Optional[int] = None
    provider_reported_at: Optional[datetime] = None
    outstanding_liability: Optional[str] = Field(None, description="Owed amount on credit or loan accounts")
    outstanding_liability_paise: Optional[int] = None
    pending_amount: str = Field("0.00", description="Unsettled activity held in draft or pending state")
    pending_amount_paise: int = 0
    opening_balance: str = Field("0.00", description="Established baseline balance at account opening")
    opening_balance_paise: int = 0
    opening_balance_date: Optional[date] = None
    opening_balance_source: Optional[str] = None

    # Credit card metrics
    credit_limit: Optional[str] = None
    credit_limit_paise: Optional[int] = None
    available_credit: Optional[str] = None
    available_credit_paise: Optional[int] = None
    statement_balance: Optional[str] = None
    statement_balance_paise: Optional[int] = None
    minimum_due: Optional[str] = None
    minimum_due_paise: Optional[int] = None
    due_date: Optional[date] = None

    # Loan metrics
    original_principal: Optional[str] = None
    original_principal_paise: Optional[int] = None
    outstanding_principal: Optional[str] = None
    outstanding_principal_paise: Optional[int] = None
    interest_rate: Optional[float] = None
    repayment_amount: Optional[str] = None
    repayment_amount_paise: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AccountBalanceSnapshotCreateRequest(BaseModel):
    """Payload for recording a point-in-time balance snapshot."""
    balance_type: str = Field(
        ...,
        description="Type: book, available, provider_reported, liability, opening",
    )
    balance_amount: str = Field(..., description="Exact monetary decimal string (e.g. '125000.50')")
    effective_at: Optional[datetime] = Field(None, description="Point-in-time effective timestamp (defaults to now)")
    source: str = Field(default="manual", description="Source: manual, bank_feed, statement, reconciliation, system")
    source_reference: Optional[str] = Field(None, description="External reference (e.g. statement_id or batch_id)")
    reconciliation_status: str = Field(default="unreconciled", description="unreconciled, reconciled, discrepant")


class AccountBalanceSnapshotResponse(BaseModel):
    """Public representation of an immutable balance snapshot."""
    id: uuid.UUID
    account_id: uuid.UUID
    workspace_id: uuid.UUID
    balance_type: str
    balance_amount: str
    balance_paise: int
    currency: str
    effective_at: datetime
    source: str
    source_reference: Optional[str] = None
    reconciliation_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Account CRUD & Lifecycle DTOs
# ---------------------------------------------------------------------------


class AccountCreateRequest(BaseModel):
    """Payload for provisioning a financial account."""
    name: str = Field(..., min_length=2, max_length=128, description="Account nickname or title")
    account_type: str = Field(
        ...,
        description="Account type (cash, savings, current, salary, credit_card, loan, investment, digital_wallet, business_bank, petty_cash, other)",
    )
    account_subtype: Optional[str] = Field(None, max_length=50, description="Specific subtype classification")
    description: Optional[str] = Field(None, max_length=500, description="Optional account notes")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="ISO 4217 currency code")
    institution_name: Optional[str] = Field(None, max_length=255, description="Bank or institution name")
    masked_identifier: Optional[str] = Field(None, max_length=50, description="Masked account or card number (e.g. '••••4092')")
    opening_date: Optional[date] = Field(None, description="Date account was opened")
    opening_balance: Optional[str] = Field(default="0.00", description="Initial opening balance amount")
    opening_balance_source: Optional[str] = Field(default="manual", description="Source of opening balance")

    # Credit card specific configuration
    credit_limit: Optional[str] = Field(None, description="Total credit limit")
    due_date: Optional[date] = Field(None, description="Monthly statement payment due date")
    minimum_due: Optional[str] = Field(None, description="Minimum due amount")
    statement_balance: Optional[str] = Field(None, description="Last statement balance")
    initial_liability: Optional[str] = Field(None, description="Initial outstanding liability")
    outstanding_liability: Optional[str] = Field(None, description="Outstanding liability amount")

    # Loan specific configuration
    original_principal: Optional[str] = Field(None, description="Initial loan disbursed amount")
    outstanding_principal: Optional[str] = Field(None, description="Current outstanding loan principal")
    interest_rate: Optional[float] = Field(None, description="Annual interest rate percentage")
    repayment_amount: Optional[str] = Field(None, description="Regular EMI repayment amount")
    loan_due_date: Optional[date] = Field(None, description="Next EMI payment due date")

    # External Provider Connection References
    provider_name: Optional[str] = Field(None, max_length=100, description="Provider identifier (e.g. 'hdfc_bank')")
    provider_account_id: Optional[str] = Field(None, max_length=255, description="Opaque external account reference")
    connection_id: Optional[str] = Field(None, max_length=255, description="External connection or sync session ID")

    metadata: Optional[dict] = Field(default_factory=dict, description="Arbitrary non-sensitive metadata")


class AccountUpdateRequest(BaseModel):
    """Payload for updating account details."""
    name: Optional[str] = Field(None, min_length=2, max_length=128, description="Updated account title")
    account_subtype: Optional[str] = Field(None, max_length=50, description="Updated subtype classification")
    description: Optional[str] = Field(None, max_length=500, description="Updated description")
    institution_name: Optional[str] = Field(None, max_length=255, description="Updated institution name")
    masked_identifier: Optional[str] = Field(None, max_length=50, description="Updated masked account identifier")
    opening_date: Optional[date] = None
    credit_limit: Optional[str] = None
    due_date: Optional[date] = None
    interest_rate: Optional[float] = None
    repayment_amount: Optional[str] = None
    metadata: Optional[dict] = None


class AccountCloseRequest(BaseModel):
    """Payload for closing a financial account."""
    closing_date: Optional[date] = Field(None, description="Effective closure date (defaults to today)")
    reason: Optional[str] = Field(None, max_length=255, description="Audited closure rationale")


class AccountResponse(BaseModel):
    """Public representation of a financial account."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    account_type: str
    account_subtype: Optional[str] = None
    description: Optional[str] = None
    currency: str
    institution_name: Optional[str] = None
    masked_identifier: Optional[str] = None
    status: str
    opening_date: Optional[date] = None
    closing_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    # Balance values (formatted exact monetary decimals)
    current_book_balance: str = "0.00"
    current_book_balance_paise: int = 0
    available_balance: Optional[str] = None
    available_balance_paise: Optional[int] = None
    provider_reported_balance: Optional[str] = None
    provider_reported_balance_paise: Optional[int] = None
    provider_reported_at: Optional[datetime] = None
    outstanding_liability: Optional[str] = None
    outstanding_liability_paise: Optional[int] = None
    pending_amount: str = "0.00"
    pending_amount_paise: int = 0

    # Credit card and loan-specific attributes
    credit_limit: Optional[str] = None
    available_credit: Optional[str] = None
    due_date: Optional[date] = None
    interest_rate: Optional[float] = None
    repayment_amount: Optional[str] = None

    # External Provider Connection References
    provider_name: Optional[str] = None
    connection_status: Optional[str] = None
    last_synced_at: Optional[datetime] = None

    source_metadata: dict = Field(default_factory=dict)
    balances: Optional[BalanceBreakdown] = None

    model_config = ConfigDict(from_attributes=True)
