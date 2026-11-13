"""
Arthsavora Financial Account Schemas
Request and response models for bank, credit card, cash, and wallet accounts.
"""

from datetime import datetime, date
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class AccountCreateRequest(BaseModel):
    """Payload for provisioning a financial account."""
    name: str = Field(..., min_length=2, max_length=128, description="Account nickname or title")
    account_type: str = Field(
        ...,
        description="Type of account (cash, bank, savings, current, credit_card, loan, wallet, investment, other)",
    )
    currency: str = Field(default="INR", min_length=3, max_length=3, description="ISO currency code")
    institution_name: Optional[str] = Field(None, max_length=255, description="Bank or institution name")
    masked_identifier: Optional[str] = Field(None, max_length=50, description="Masked account or card number (e.g. 'XX4092')")


class AccountResponse(BaseModel):
    """Public representation of a financial account."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    account_type: str
    currency: str
    institution_name: Optional[str] = None
    masked_identifier: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
