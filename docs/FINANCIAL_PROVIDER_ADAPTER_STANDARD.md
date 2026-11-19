# ARTHSAVORA Financial Provider Adapter Standard

## 1. Overview

The ARTHSAVORA Financial Provider Adapter Standard defines the contract, responsibilities, and data formats required to integrate external financial data sources into the ARTHSAVORA ecosystem.

Every integration partner—whether an Indian Account Aggregator (AA), an international Open Banking gateway (UK/EU), or a direct bank API—must implement the abstract interface defined in `FinancialProviderAdapter`.

---

## 2. The Abstract Adapter Contract

```python
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from app.domain.financial_connection import NormalizedAccountVO, NormalizedTransactionVO

class FinancialProviderAdapter(ABC):
    """
    Abstract interface for all financial data providers and aggregators.
    """

    @abstractmethod
    async def initiate_consent(
        self,
        workspace_id: UUID,
        user_id: UUID,
        institution_id: str,
        purpose: str,
        data_categories: List[str],
        account_types: List[str],
        valid_days: int = 180,
    ) -> Dict[str, Any]:
        """
        Requests a consent artefact / handle from the provider.
        Returns dict containing provider_consent_handle, authorization_url, valid_from, valid_to.
        """
        pass

    @abstractmethod
    async def check_consent_status(
        self,
        provider_consent_handle: str,
    ) -> Dict[str, Any]:
        """
        Polls or verifies consent handle state with provider.
        Returns dict with status ('active', 'pending', 'rejected', 'revoked', 'expired').
        """
        pass

    @abstractmethod
    async def revoke_consent(
        self,
        provider_consent_handle: str,
    ) -> bool:
        """
        Notifies provider to revoke and terminate active consent artefact.
        """
        pass

    @abstractmethod
    async def discover_accounts(
        self,
        provider_consent_handle: str,
        institution_id: Optional[str] = None,
    ) -> List[NormalizedAccountVO]:
        """
        Retrieves list of accounts linked under this authorized consent.
        """
        pass

    @abstractmethod
    async def fetch_transactions(
        self,
        provider_consent_handle: str,
        provider_account_id: str,
        from_date: date,
        to_date: date,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Tuple[List[NormalizedTransactionVO], Optional[str]]:
        """
        Fetches normalized transactions within the date range.
        Returns (list_of_transactions, next_page_cursor).
        """
        pass

    @abstractmethod
    async def fetch_balances(
        self,
        provider_consent_handle: str,
        provider_account_ids: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetches current and available balances for specified accounts.
        Returns mapping of provider_account_id -> {current_balance_paise, available_balance_paise, balance_as_of}.
        """
        pass
```

---

## 3. Normalized Value Objects

### 3.1 `NormalizedAccountVO`
Adapters must transform raw provider account structures into `NormalizedAccountVO`:
- `provider_account_id`: String uniquely identifying the account at the provider/FIP.
- `fip_id`: Financial Information Provider code (e.g., `HDFC-FIP`).
- `institution_name`: Human-readable name of the bank (e.g., `HDFC Bank Ltd`).
- `masked_account_number`: Masked display number (e.g., `•••• 4321`).
- `account_type`: Canonical type (`savings`, `current`, `credit_card`, `loan`, `investment`).
- `currency`: ISO 4217 three-letter currency code (default: `INR`).
- `account_holder_name`: Name on the bank account.
- `current_balance_paise`: Current ledger balance in minor units (integer paise).
- `available_balance_paise`: Spendable balance in minor units (integer paise).
- `balance_as_of`: UTC timestamp of the balance report.
- `metadata`: Raw JSON metadata from provider.

### 3.2 `NormalizedTransactionVO`
Adapters must transform raw provider transaction items into `NormalizedTransactionVO`:
- `external_transaction_id`: Globally unique transaction reference from the provider/bank.
- `provider_account_id`: String identifying the external account.
- `amount_paise`: Non-negative integer in minor units (paise).
- `currency`: ISO 4217 code.
- `direction`: Direction indicator (`inflow` or `outflow`).
- `transaction_date`: Calendar date the transaction occurred.
- `description`: Narrative or bank statement line text.
- `merchant_name`: Cleaned merchant identifier if identifiable.
- `reference_number`: Bank reference, UTR, RRN, or check number.
- `category_hint`: Provider-suggested category code if available.
- `raw_payload`: Original unparsed payload for audit and tracing.

---

## 4. Error Handling Guidelines

All adapter methods must translate low-level HTTP or network failures into standardized domain exceptions:
- **`BusinessRuleViolationException`**: Used when consent is expired, rejected, or invalid.
- **`ValidationException`**: Used when required parameters (e.g., account IDs, date ranges) are invalid.
- **`NotFoundException`**: Used when a requested external account or handle does not exist.
- **`ConnectionUnavailableException`**: Used when the remote provider API is experiencing downtime, 5xx errors, or timeout.

---

## 5. Adding New Providers

To add a new provider:
1. Subclass `FinancialProviderAdapter` in `app/services/financial_providers/<provider_name>_adapter.py`.
2. Register the adapter in `FinancialProviderRegistry.register_adapter(...)` in `registry.py`.
3. Add a seed catalog entry in `FinancialProviderRegistry.DEFAULT_CATALOG`.
4. Ensure provider returns normalized value objects adhering strictly to the integer paise convention.
