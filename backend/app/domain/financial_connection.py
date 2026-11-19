"""
Arthsavora Financial Connection, Account Aggregation & Normalization Domain Model
Pure functional domain contracts, immutable Value Objects, statutory ReBIT AA enums,
masking utilities, and reconciliation calculations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from uuid import UUID


class ConnectionStatus(str, Enum):
    """Lifecycle states of an external financial connection."""
    NOT_CONNECTED = "not_connected"
    INITIATED = "initiated"
    AWAITING_AUTHORIZATION = "awaiting_authorization"
    AUTHORIZED = "authorized"
    SYNCHRONIZING = "synchronizing"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    FAILED = "failed"
    DISCONNECTED = "disconnected"


class ConnectionHealthStatus(str, Enum):
    """Real-time operational health indicator for user dashboards."""
    HEALTHY = "healthy"
    NEEDS_AUTHORIZATION = "needs_authorization"
    SYNC_DELAYED = "sync_delayed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CONNECTION_EXPIRED = "connection_expired"
    DISCONNECTED = "disconnected"


class ConsentStatus(str, Enum):
    """ReBIT Account Aggregator (AA) and Open Banking consent lifecycle states."""
    INITIATED = "initiated"
    PENDING_USER_APPROVAL = "pending_user_approval"
    ACTIVE = "active"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ProviderCategory(str, Enum):
    """Classification of external financial data integration partner."""
    ACCOUNT_AGGREGATOR = "account_aggregator"
    BANKING_API = "banking_api"
    CARD_NETWORK = "card_network"
    MANUAL_IMPORT = "manual_import"


class ProviderStatus(str, Enum):
    """Operational capability state of a financial provider."""
    AVAILABLE = "available"
    SANDBOX_ONLY = "sandbox_only"
    PRODUCTION_CONFIGURED = "production_configured"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    DISABLED = "disabled"


class SyncJobType(str, Enum):
    """Trigger categorization for data synchronization batches."""
    INITIAL_SYNC = "initial_sync"
    SCHEDULED_SYNC = "scheduled_sync"
    MANUAL_SYNC = "manual_sync"
    RECONCILIATION_SYNC = "reconciliation_sync"


class SyncJobStatus(str, Enum):
    """Execution status machine for synchronization workers."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReconciliationStatus(str, Enum):
    """Balance verification and discrepancy status."""
    MATCHED = "matched"
    PARTIALLY_MATCHED = "partially_matched"
    UNMATCHED = "unmatched"
    REQUIRES_REVIEW = "requires_review"
    RESOLVED = "resolved"


class AccountLinkStatus(str, Enum):
    """Mapping status between discovered external account and internal account."""
    DISCOVERED = "discovered"
    LINKED = "linked"
    UNLINKED = "unlinked"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Immutable Value Objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NormalizedAccountVO:
    """Provider-agnostic representation of a discovered financial account."""
    provider_account_id: str
    fip_id: str
    institution_name: str
    masked_account_number: str
    account_type: str  # savings, current, credit_card, loan, deposit
    currency: str = "INR"
    current_balance_paise: Optional[int] = None
    available_balance_paise: Optional[int] = None
    balance_as_of: Optional[datetime] = None
    account_holder_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedTransactionVO:
    """Normalized financial transaction conforming to Arthsavora ledger requirements."""
    external_transaction_id: str
    amount_paise: int
    direction: str  # inflow, outflow
    transaction_date: date
    description: str
    merchant_name: Optional[str] = None
    status: str = "posted"  # posted, pending
    reference_number: Optional[str] = None
    category_code: Optional[str] = None
    currency: str = "INR"
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationVarianceVO:
    """Deterministic variance computation comparing reported balance with book balance."""
    account_id: UUID
    provider_reported_balance_paise: int
    calculated_book_balance_paise: int
    difference_paise: int
    status: ReconciliationStatus
    unmatched_transactions_count: int
    explanation: str


@dataclass(frozen=True)
class ConsentSummaryVO:
    """Evaluated validity and remaining duration for an active consent."""
    consent_id: UUID
    provider_code: str
    status: ConsentStatus
    valid_from: datetime
    valid_to: datetime
    is_expired: bool
    days_until_expiry: int


# ---------------------------------------------------------------------------
# Pure Domain Functions
# ---------------------------------------------------------------------------

def mask_account_identifier(account_identifier: Optional[str]) -> str:
    """
    Safely masks bank account or credit card numbers for PCI-DSS/RBI privacy compliance.
    Preserves at most the last 4 alphanumeric characters: '••••1234'.
    """
    if not account_identifier:
        return "••••"
    cleaned = re.sub(r"\s+", "", str(account_identifier))
    if len(cleaned) <= 4:
        return f"••••{cleaned}"
    last_four = cleaned[-4:]
    return f"••••{last_four}"


def normalize_transaction_direction(
    raw_direction: Optional[str] = None,
    raw_type: Optional[str] = None,
    amount_paise: int = 0,
) -> tuple[str, int]:
    """
    Standardizes disparate provider direction indicators (CR/DR, CREDIT/DEBIT, INFLOW/OUTFLOW, +/-)
    into Arthsavora canonical direction ('inflow' or 'outflow') with positive integer minor units.
    """
    abs_paise = abs(amount_paise)
    dir_str = (raw_direction or "").strip().lower()
    type_str = (raw_type or "").strip().lower()

    if dir_str in ("cr", "credit", "inflow", "deposit", "refund") or type_str in ("cr", "credit", "deposit"):
        return "inflow", abs_paise
    if dir_str in ("dr", "debit", "outflow", "withdrawal", "payment") or type_str in ("dr", "debit", "withdrawal"):
        return "outflow", abs_paise
    
    # If direction indicator is absent, inspect signed amount
    if amount_paise < 0:
        return "outflow", abs_paise
    return "inflow", abs_paise


def calculate_reconciliation_variance(
    provider_reported_balance_paise: int,
    calculated_book_balance_paise: int,
    unmatched_transactions_count: int = 0,
) -> ReconciliationVarianceVO:
    """
    Compares provider reported bank balance against internal general ledger book balance.
    Computes exact integer difference and determines reconciliation health status.
    """
    diff_paise = provider_reported_balance_paise - calculated_book_balance_paise
    diff_abs = abs(diff_paise)

    if diff_abs == 0 and unmatched_transactions_count == 0:
        status = ReconciliationStatus.MATCHED
        explanation = "Bank balance and Arthsavora book balance are perfectly reconciled."
    elif diff_abs == 0 and unmatched_transactions_count > 0:
        status = ReconciliationStatus.PARTIALLY_MATCHED
        explanation = f"Net balance agrees, but {unmatched_transactions_count} imported transactions require manual review."
    elif diff_abs > 0 and unmatched_transactions_count > 0:
        status = ReconciliationStatus.REQUIRES_REVIEW
        explanation = (
            f"Variance of ₹{diff_abs / 100:,.2f} detected with {unmatched_transactions_count} "
            f"unmatched transactions awaiting verification."
        )
    else:
        status = ReconciliationStatus.UNMATCHED
        explanation = (
            f"Variance of ₹{diff_abs / 100:,.2f} detected between reported balance (₹{provider_reported_balance_paise / 100:,.2f}) "
            f"and book balance (₹{calculated_book_balance_paise / 100:,.2f})."
        )

    # Note: caller will supply actual account_id
    return ReconciliationVarianceVO(
        account_id=UUID("00000000-0000-0000-0000-000000000000"),
        provider_reported_balance_paise=provider_reported_balance_paise,
        calculated_book_balance_paise=calculated_book_balance_paise,
        difference_paise=diff_paise,
        status=status,
        unmatched_transactions_count=unmatched_transactions_count,
        explanation=explanation,
    )


def compute_connection_health(
    connection_status: ConnectionStatus,
    last_successful_sync_at: Optional[datetime],
    consent_expiry: Optional[datetime],
    sync_failure_count: int = 0,
    current_time: Optional[datetime] = None,
) -> ConnectionHealthStatus:
    """
    Evaluates connection vitality based on status machine, consent validity, and sync recency.
    """
    now = current_time or datetime.now(timezone.utc)

    if connection_status == ConnectionStatus.DISCONNECTED:
        return ConnectionHealthStatus.DISCONNECTED

    if connection_status in (ConnectionStatus.NOT_CONNECTED, ConnectionStatus.INITIATED, ConnectionStatus.AWAITING_AUTHORIZATION):
        return ConnectionHealthStatus.NEEDS_AUTHORIZATION

    if consent_expiry and consent_expiry <= now:
        return ConnectionHealthStatus.CONNECTION_EXPIRED

    if connection_status == ConnectionStatus.FAILED or sync_failure_count >= 3:
        return ConnectionHealthStatus.PROVIDER_UNAVAILABLE

    if connection_status == ConnectionStatus.EXPIRED:
        return ConnectionHealthStatus.CONNECTION_EXPIRED

    # Check for sync latency (more than 7 days since last successful sync)
    if last_successful_sync_at:
        days_since_sync = (now - last_successful_sync_at).total_seconds() / 86400
        if days_since_sync > 7:
            return ConnectionHealthStatus.SYNC_DELAYED

    return ConnectionHealthStatus.HEALTHY


def evaluate_consent_validity(
    consent_status: ConsentStatus,
    valid_from: datetime,
    valid_to: datetime,
    revoked_at: Optional[datetime] = None,
    current_time: Optional[datetime] = None,
) -> bool:
    """
    Verifies that a consent artefact is active, within its authorized temporal bounds,
    and has not been revoked.
    """
    if consent_status != ConsentStatus.ACTIVE:
        return False
    if revoked_at is not None:
        return False

    now = current_time or datetime.now(timezone.utc)
    return valid_from <= now <= valid_to
