"""
Arthsavora Operational Transaction Schemas
Request and response models for financial movements with exact decimal string representation,
integer minor units (paise), lifecycle operations, transfers, refunds, and reversals.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Union, Dict, Any, List
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TransactionCreateRequest(BaseModel):
    """Payload for recording or importing a financial transaction."""
    account_id: uuid.UUID = Field(..., description="Target financial account UUID")
    amount: Union[str, Decimal] = Field(..., description="Exact monetary amount as a decimal string (e.g. '1500.50')")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="ISO 4217 currency code")
    transaction_type: str = Field(
        ...,
        description=(
            "Functional type: income, expense, transfer, refund, reversal, adjustment, "
            "deposit, withdrawal, interest, bank_fee, tax, credit_card_purchase, credit_card_payment, "
            "credit_card_refund, credit_card_fee, credit_card_interest, loan_disbursal, "
            "loan_principal_repayment, loan_interest_payment, loan_fee, investment_contribution, "
            "investment_withdrawal, dividend, interest_income, investment_fee, cash_transaction, unknown"
        ),
    )
    direction: Optional[str] = Field(
        None,
        description="Transaction direction: inflow, outflow, neutral (auto-inferred if omitted)",
    )
    transaction_date: date = Field(..., description="Date of the financial event")
    settlement_date: Optional[date] = Field(None, description="Actual bank/settlement clearing date")
    description: str = Field(..., min_length=1, max_length=512, description="Transaction narrative or note")
    merchant_name: Optional[str] = Field(None, max_length=255, description="Merchant, counterparty, or vendor name")
    category_id: Optional[uuid.UUID] = Field(None, description="Optional category reference")
    status: Optional[str] = Field(
        default="posted",
        description="Initial lifecycle status: posted (default) or pending",
    )
    source_type: Optional[str] = Field(
        default="manual",
        description="Source provenance: manual, csv_import, pdf_import, bank_feed, account_aggregator, credit_card_statement, ocr, internal_adjustment, system",
    )
    source_reference: Optional[str] = Field(None, max_length=255, description="External batch or file identifier")
    external_transaction_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Unique bank/UPI reference for idempotent deduplication within workspace",
    )
    related_transaction_id: Optional[uuid.UUID] = Field(
        None,
        description="UUID of associated transaction (e.g. paired transfer leg, refunded item, reversal)",
    )
    is_ai_predicted: bool = Field(False, description="Flag indicating if categorization is AI-derived")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI confidence score between 0.0 and 1.0")
    source_provenance: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Raw ingested provenance (raw description, batch ID, import timestamp, raw payload)",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="User-defined non-sensitive tags, project codes, or memo notes",
    )


class TransactionUpdateRequest(BaseModel):
    """
    Payload for updating transaction metadata.
    Editable metadata only: description, merchant, category, user metadata.
    Financial facts (amount, currency, account, date, status) cannot be changed on posted transactions.
    """
    description: Optional[str] = Field(None, min_length=1, max_length=512, description="Updated narrative")
    merchant_name: Optional[str] = Field(None, max_length=255, description="Updated counterparty")
    category_id: Optional[uuid.UUID] = Field(None, description="Updated category UUID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated non-financial metadata/tags")

    # Guard fields: if supplied for posted records, rejected by service
    amount: Optional[Union[str, Decimal]] = None
    currency: Optional[str] = None
    account_id: Optional[uuid.UUID] = None
    transaction_date: Optional[date] = None
    transaction_type: Optional[str] = None
    direction: Optional[str] = None
    status: Optional[str] = None


class TransactionPostRequest(BaseModel):
    """Payload to transition a pending transaction to posted."""
    settlement_date: Optional[date] = Field(None, description="Effective settlement clearing date")


class TransactionCancelRequest(BaseModel):
    """Payload to cancel an unposted/pending transaction."""
    cancellation_reason: Optional[str] = Field(None, max_length=255, description="Reason for cancellation")


class TransactionReverseRequest(BaseModel):
    """Payload to issue a formal reversal of a posted transaction."""
    reason: str = Field(..., min_length=3, max_length=255, description="Auditable justification for reversing this transaction")


class TransactionRefundRequest(BaseModel):
    """Payload to issue a partial or full refund for a posted transaction."""
    refund_amount: Union[str, Decimal] = Field(..., description="Exact refund monetary decimal amount")
    refund_date: Optional[date] = Field(None, description="Date of refund (defaults to today)")
    description: Optional[str] = Field(None, max_length=512, description="Refund narrative or credit note")
    external_refund_id: Optional[str] = Field(None, max_length=255, description="External refund or gateway reference")


class TransferCreateRequest(BaseModel):
    """Payload for executing an internal transfer between two accounts in the same workspace."""
    source_account_id: uuid.UUID = Field(..., description="Source financial account (outflow)")
    destination_account_id: uuid.UUID = Field(..., description="Destination financial account (inflow)")
    amount: Union[str, Decimal] = Field(..., description="Transfer amount in source account currency")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="ISO 4217 currency code")
    transfer_date: date = Field(..., description="Date of the transfer")
    description: Optional[str] = Field(default="Account transfer", max_length=512, description="Transfer narrative")
    status: Optional[str] = Field(default="posted", description="Initial lifecycle state: posted or pending")
    external_transaction_id: Optional[str] = Field(None, max_length=255, description="Unique external reference")
    exchange_rate: Optional[float] = Field(None, gt=0, description="Conversion exchange rate if multi-currency")
    destination_amount: Optional[Union[str, Decimal]] = Field(None, description="Explicit destination currency amount")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")


class TransferResponse(BaseModel):
    """Response model for a logical transfer linking two paired transaction legs."""
    transfer_id: uuid.UUID
    workspace_id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: str
    currency: str
    transfer_date: date
    status: str
    description: str
    source_transaction_id: uuid.UUID
    destination_transaction_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    """Public representation of an operational transaction."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    account_id: uuid.UUID
    amount: str
    amount_paise: int
    currency: str
    transaction_type: str
    direction: str
    transaction_date: date
    settlement_date: Optional[date] = None
    description: str
    merchant_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    status: str
    source_type: str
    source_reference: Optional[str] = None
    external_transaction_id: Optional[str] = None
    related_transaction_id: Optional[uuid.UUID] = None
    original_transaction_id: Optional[uuid.UUID] = None
    transfer_id: Optional[uuid.UUID] = None
    created_by_id: Optional[uuid.UUID] = None
    reversal_reason: Optional[str] = None
    is_ai_predicted: bool
    ai_confidence: Optional[float] = None
    source_provenance: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_payload")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TransactionHistoryEntry(BaseModel):
    """Item in the auditable history trail of a transaction."""
    id: uuid.UUID
    action: str
    actor_id: Optional[uuid.UUID] = None
    timestamp: datetime
    details: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
