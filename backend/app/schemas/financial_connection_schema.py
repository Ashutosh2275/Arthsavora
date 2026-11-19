"""
Arthsavora Financial Connection & Aggregation Pydantic Schemas
Defines request and response serialization contracts for financial providers,
connections, consents, discovered accounts, sync jobs, and reconciliation.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Provider Schemas
# ---------------------------------------------------------------------------
class FinancialProviderResponse(BaseModel):
    id: UUID
    provider_code: str
    name: str
    category: str
    country: str
    supported_institutions: List[Dict[str, Any]]
    supported_account_types: List[str]
    auth_method: str
    consent_capabilities: Dict[str, Any]
    data_capabilities: List[str]
    historical_days_limit: int
    sync_capabilities: Dict[str, Any]
    status: str
    is_sandbox: bool
    docs_reference: Optional[str] = None
    config_status: str
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Connection Schemas
# ---------------------------------------------------------------------------
class InitiateConnectionRequest(BaseModel):
    provider_code: str = Field(..., description="Provider code, e.g. MOCK_SANDBOX_AA or SETU_AA")
    institution_id: str = Field(..., description="Target bank/institution code, e.g. HDFC, SBI")
    institution_name: Optional[str] = None
    purpose: str = Field(default="Personal Financial Management & Automated Reconciliation")
    purpose_code: str = Field(default="101")
    data_categories: List[str] = Field(default_factory=lambda: ["TRANSACTIONS", "BALANCES", "PROFILE"])
    account_types: List[str] = Field(default_factory=lambda: ["savings", "current", "credit_card"])
    valid_days: int = Field(default=180, ge=1, le=365)
    sync_schedule: str = Field(default="manual")


class AuthorizeConnectionRequest(BaseModel):
    provider_consent_handle: Optional[str] = None
    auth_token: Optional[str] = None


class DiscoveredAccountResponse(BaseModel):
    id: UUID
    connection_id: UUID
    account_id: Optional[UUID] = None
    provider_account_id: str
    fip_id: str
    institution_name: str
    masked_account_number: str
    account_type: str
    currency: str
    status: str
    account_holder_name: Optional[str] = None
    current_balance_paise: Optional[int] = None
    available_balance_paise: Optional[int] = None
    balance_as_of: Optional[datetime] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class LinkAccountRequest(BaseModel):
    existing_account_id: Optional[UUID] = None
    create_new: bool = Field(default=False)
    account_name: Optional[str] = None


class FinancialConsentResponse(BaseModel):
    id: UUID
    connection_id: UUID
    provider_consent_handle: Optional[str] = None
    purpose: str
    purpose_code: str
    data_categories: List[str]
    account_types: List[str]
    status: str
    fetch_frequency: str
    valid_from: datetime
    valid_to: datetime
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None

    class Config:
        from_attributes = True


class FinancialConnectionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    provider_id: UUID
    provider_code: Optional[str] = None
    provider_name: Optional[str] = None
    institution_id: str
    institution_name: str
    status: str
    health_status: str
    authorization_url: Optional[str] = None
    authorized_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_attempted_sync_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    sync_failure_count: int
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    sync_schedule: str
    created_at: datetime
    active_consent: Optional[FinancialConsentResponse] = None
    account_references: List[DiscoveredAccountResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Sync & Reconciliation Schemas
# ---------------------------------------------------------------------------
class SyncJobResponse(BaseModel):
    id: UUID
    connection_id: UUID
    job_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_retrieved: int
    records_imported: int
    duplicates_detected: int
    errors_count: int
    error_summary: Optional[str] = None
    retry_count: int

    class Config:
        from_attributes = True


class TriggerSyncRequest(BaseModel):
    job_type: str = Field(default="manual_sync")


class ReconciliationRecordResponse(BaseModel):
    id: UUID
    account_id: UUID
    connection_id: UUID
    reconciliation_date: date
    provider_reported_balance_paise: int
    calculated_book_balance_paise: int
    difference_paise: int
    status: str
    unmatched_transactions_count: int
    explanation: Optional[str] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResolveReconciliationRequest(BaseModel):
    explanation: str = Field(..., min_length=3, max_length=1000)


class RevokeConsentRequest(BaseModel):
    reason: Optional[str] = Field(default="User initiated consent revocation")
