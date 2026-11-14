"""
Arthsavora Double-Entry General Ledger API Schemas
Pydantic v2 data transfer models for Chart of Accounts, Accounting Periods,
Journal Entries, Lines, Trial Balances, and Derived Account Balances.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Chart of Accounts Schemas
# ---------------------------------------------------------------------------

class LedgerAccountCreate(BaseModel):
    code: str = Field(..., max_length=50, description="Unique account code, e.g. '1010', '2010'")
    name: str = Field(..., max_length=255, description="Human readable account name")
    account_type: str = Field(..., description="asset, liability, equity, revenue, expense")
    normal_balance: Optional[str] = Field(None, description="debit or credit (inferred from account_type if omitted)")
    sub_type: Optional[str] = Field(None, max_length=50, description="Sub-classification e.g. 'cash', 'bank', 'credit_card'")
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[uuid.UUID] = Field(None, description="Parent account in COA tree")
    linked_account_id: Optional[uuid.UUID] = Field(None, description="Linked operational FinancialAccount")


class LedgerAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class LedgerAccountResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    code: str
    name: str
    account_type: str
    normal_balance: str
    sub_type: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    linked_account_id: Optional[uuid.UUID] = None
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Accounting Period Schemas
# ---------------------------------------------------------------------------

class AccountingPeriodCreate(BaseModel):
    fiscal_year: str = Field(..., max_length=20, description="Fiscal year label e.g. '2026-2027'")
    period_number: int = Field(..., ge=1, le=12, description="Period number (1 to 12)")
    name: str = Field(..., max_length=100, description="Name e.g. 'April 2026'")
    start_date: date
    end_date: date


class AccountingPeriodResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    fiscal_year: str
    period_number: int
    name: str
    start_date: date
    end_date: date
    status: str
    closed_at: Optional[datetime] = None
    closed_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Journal Line Schemas
# ---------------------------------------------------------------------------

class JournalLineCreate(BaseModel):
    ledger_account_id: uuid.UUID
    entry_type: str = Field(..., description="'debit' or 'credit'")
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4, description="Exact positive amount")
    amount_paise: Optional[int] = Field(None, gt=0, description="Integer minor units (auto-computed if omitted)")
    currency: str = Field(default="INR", max_length=3)
    description: Optional[str] = Field(None, max_length=255)
    financial_account_id: Optional[uuid.UUID] = None
    counterparty_name: Optional[str] = Field(None, max_length=255)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class JournalLineResponse(BaseModel):
    id: uuid.UUID
    journal_entry_id: uuid.UUID
    ledger_account_id: uuid.UUID
    line_number: int
    entry_type: str
    amount: Decimal
    amount_paise: int
    currency: str
    description: Optional[str] = None
    financial_account_id: Optional[uuid.UUID] = None
    counterparty_name: Optional[str] = None
    ledger_account_code: Optional[str] = None
    ledger_account_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Journal Entry Schemas
# ---------------------------------------------------------------------------

class JournalEntryCreate(BaseModel):
    entry_number: Optional[str] = Field(None, max_length=50, description="Auto-generated if omitted")
    entry_date: date = Field(default_factory=date.today)
    description: str = Field(..., min_length=1, max_length=512)
    source_type: str = Field(default="manual", max_length=50)
    source_id: Optional[uuid.UUID] = None
    lines: List[JournalLineCreate] = Field(..., min_length=2, description="At least two balanced debit/credit lines")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JournalEntryUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=512)
    entry_date: Optional[date] = None


class JournalEntryPostRequest(BaseModel):
    correlation_id: Optional[str] = None


class JournalEntryReverseRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory auditable justification")
    reversal_number: Optional[str] = Field(None, max_length=50, description="Auto-generated if omitted")


class JournalEntryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    entry_number: str
    entry_date: date
    posting_date: Optional[datetime] = None
    status: str  # draft, posted, reversed
    description: str
    source_type: str
    source_id: Optional[uuid.UUID] = None
    reversal_of_entry_id: Optional[uuid.UUID] = None
    reversal_reason: Optional[str] = None
    accounting_period_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    posted_by_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_payload")
    lines: List[JournalLineResponse] = Field(default_factory=list)
    total_debits: Decimal = Decimal("0.0000")
    total_credits: Decimal = Decimal("0.0000")
    is_balanced: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JournalListResponse(BaseModel):
    items: List[JournalEntryResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Balance & Trial Balance Schemas
# ---------------------------------------------------------------------------

class AccountBalanceResponse(BaseModel):
    account_id: str
    code: str
    name: str
    account_type: str
    normal_balance: str
    total_debits: Decimal
    total_credits: Decimal
    total_debits_paise: int
    total_credits_paise: int
    net_balance: Decimal
    net_balance_paise: int


class TrialBalanceEntry(BaseModel):
    account_id: str
    code: str
    name: str
    account_type: str
    normal_balance: str
    debit_balance: Decimal
    credit_balance: Decimal
    debit_balance_paise: int
    credit_balance_paise: int


class TrialBalanceResponse(BaseModel):
    as_of_date: str
    is_balanced: bool
    total_debits: Decimal
    total_credits: Decimal
    total_debits_paise: int
    total_credits_paise: int
    difference: Decimal
    difference_paise: int
    entries: List[TrialBalanceEntry]
