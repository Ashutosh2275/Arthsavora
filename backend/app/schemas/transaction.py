"""
Arthsavora Operational Transaction Schemas
Request and response models for financial movements with exact decimal string representation.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TransactionCreateRequest(BaseModel):
    """Payload for recording or importing a transaction."""
    account_id: uuid.UUID = Field(..., description="Target account UUID")
    amount: Union[str, Decimal] = Field(..., description="Exact monetary amount as a decimal string or Decimal")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="ISO currency code")
    transaction_type: str = Field(
        ...,
        description="Classification: income, expense, transfer, refund, repayment, adjustment",
    )
    transaction_date: date = Field(..., description="Date of the financial event")
    description: str = Field(..., min_length=1, max_length=512, description="Transaction narrative or note")
    merchant_name: Optional[str] = Field(None, max_length=255, description="Merchant or counterparty name")
    category_id: Optional[uuid.UUID] = Field(None, description="Optional category UUID")
    external_transaction_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Unique bank/UPI reference for idempotent deduplication",
    )
    is_ai_predicted: bool = Field(False, description="Flag indicating if categorization is AI-derived")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI confidence score")


class TransactionResponse(BaseModel):
    """Public representation of an operational transaction."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    account_id: uuid.UUID
    amount: Decimal
    currency: str
    transaction_type: str
    transaction_date: date
    settlement_date: Optional[date] = None
    description: str
    merchant_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    status: str
    external_transaction_id: Optional[str] = None
    is_ai_predicted: bool
    ai_confidence: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
