"""
Arthsavora Financial Provider Adapter Interface
Abstract Base Class defining provider-agnostic contracts for consent management,
account discovery, transaction synchronization, and balance retrieval.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.domain.financial_connection import (
    NormalizedAccountVO,
    NormalizedTransactionVO,
)


class FinancialProviderAdapter(ABC):
    """Abstract interface that every external provider integration must implement."""

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique uppercase code identifying the provider implementation."""
        pass

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
        Initiates a consent request with the provider.
        Returns dict containing:
        - provider_consent_handle: str
        - authorization_url: Optional[str]
        - valid_from: datetime
        - valid_to: datetime
        - raw_response: dict
        """
        pass

    @abstractmethod
    async def check_consent_status(
        self,
        provider_consent_handle: str,
    ) -> Dict[str, Any]:
        """
        Checks current status of a consent request at the provider.
        Returns dict containing:
        - status: ConsentStatus value (e.g. 'active', 'pending_user_approval', 'rejected', 'expired')
        - raw_artefact: dict (signed/tamper-evident consent artefact if active)
        """
        pass

    @abstractmethod
    async def revoke_consent(
        self,
        provider_consent_handle: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Revokes an active consent handle with the provider."""
        pass

    @abstractmethod
    async def discover_accounts(
        self,
        provider_consent_handle: str,
        institution_id: str,
    ) -> List[NormalizedAccountVO]:
        """
        Queries FIPs/institutions via the provider using an authorized consent handle.
        Returns list of normalized discovered accounts.
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
    ) -> Tuple[List[NormalizedTransactionVO], Optional[str]]:
        """
        Retrieves financial transactions within the specified date range.
        Returns tuple of (transactions list, next_cursor).
        """
        pass

    @abstractmethod
    async def fetch_balances(
        self,
        provider_consent_handle: str,
        provider_account_ids: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Queries real-time provider balances for specified accounts.
        Returns dict mapping provider_account_id -> {
            'current_balance_paise': int,
            'available_balance_paise': Optional[int],
            'balance_as_of': datetime
        }
        """
        pass
