"""
Arthsavora Financial Provider Registry
Central catalog of supported financial data providers, Account Aggregators (AA),
and adapter factory resolution.
"""

from typing import Any, Dict, List, Optional
from app.domain.financial_connection import ProviderCategory, ProviderStatus
from app.services.financial_providers.base import FinancialProviderAdapter
from app.services.financial_providers.india_aa_adapter import IndiaAccountAggregatorAdapter
from app.services.financial_providers.mock_sandbox_adapter import MockSandboxAdapter


# Static catalog of financial providers with capabilities and statutory metadata
REGISTERED_PROVIDERS_CATALOG: List[Dict[str, Any]] = [
    {
        "provider_code": "MOCK_SANDBOX_AA",
        "name": "Arthsavora Sandbox AA Simulator",
        "category": ProviderCategory.ACCOUNT_AGGREGATOR.value,
        "country": "IN",
        "supported_institutions": [
            {"id": "HDFC", "name": "HDFC Bank Ltd", "code": "HDFC"},
            {"id": "SBI", "name": "State Bank of India", "code": "SBI"},
            {"id": "ICICI", "name": "ICICI Bank Ltd", "code": "ICICI"},
            {"id": "AXIS", "name": "Axis Bank Ltd", "code": "AXIS"},
            {"id": "KOTAK", "name": "Kotak Mahindra Bank", "code": "KOTAK"},
        ],
        "supported_account_types": ["savings", "current", "credit_card", "loan", "deposit"],
        "auth_method": "consent_handle",
        "consent_capabilities": {
            "periodic_fetch": True,
            "one_time_fetch": True,
            "max_validity_days": 365,
            "revocable": True,
        },
        "data_capabilities": ["PROFILE", "SUMMARY", "TRANSACTIONS", "BALANCES"],
        "historical_days_limit": 365,
        "sync_capabilities": {"scheduled": True, "manual": True, "webhooks": True},
        "status": ProviderStatus.AVAILABLE.value,
        "is_sandbox": True,
        "docs_reference": "https://docs.arthsavora.internal/providers/sandbox-aa",
        "config_status": "sandbox_ready",
        "provider_metadata": {
            "description": "Zero-dependency deterministic simulation of ReBIT Account Aggregator architecture for test verification and development.",
            "adapter_class": "MockSandboxAdapter",
        },
    },
    {
        "provider_code": "SETU_AA",
        "name": "Setu Account Aggregator (ReBIT FIU)",
        "category": ProviderCategory.ACCOUNT_AGGREGATOR.value,
        "country": "IN",
        "supported_institutions": [
            {"id": "HDFC", "name": "HDFC Bank Ltd", "code": "HDFC"},
            {"id": "SBI", "name": "State Bank of India", "code": "SBI"},
            {"id": "ICICI", "name": "ICICI Bank Ltd", "code": "ICICI"},
            {"id": "AXIS", "name": "Axis Bank Ltd", "code": "AXIS"},
            {"id": "PNB", "name": "Punjab National Bank", "code": "PNB"},
            {"id": "BOB", "name": "Bank of Baroda", "code": "BOB"},
            {"id": "INDUSIND", "name": "IndusInd Bank", "code": "INDUSIND"},
            {"id": "IDFC", "name": "IDFC FIRST Bank", "code": "IDFC"},
        ],
        "supported_account_types": ["savings", "current", "deposit", "recurring_deposit", "term_deposit"],
        "auth_method": "consent_handle",
        "consent_capabilities": {
            "periodic_fetch": True,
            "one_time_fetch": True,
            "max_validity_days": 365,
            "revocable": True,
        },
        "data_capabilities": ["PROFILE", "SUMMARY", "TRANSACTIONS"],
        "historical_days_limit": 180,
        "sync_capabilities": {"scheduled": True, "manual": True, "webhooks": True},
        "status": ProviderStatus.SANDBOX_ONLY.value,
        "is_sandbox": True,
        "docs_reference": "https://docs.setu.co/data/account-aggregator",
        "config_status": "sandbox_ready",
        "provider_metadata": {
            "fiu_id": "SETU_FIU",
            "rebit_version": "1.1.2",
            "description": "RBI-regulated Account Aggregator Technical Service Provider gateway connecting all major Indian scheduled commercial banks.",
        },
    },
    {
        "provider_code": "ONEMONEY_AA",
        "name": "OneMoney Account Aggregator",
        "category": ProviderCategory.ACCOUNT_AGGREGATOR.value,
        "country": "IN",
        "supported_institutions": [
            {"id": "SBI", "name": "State Bank of India", "code": "SBI"},
            {"id": "ICICI", "name": "ICICI Bank Ltd", "code": "ICICI"},
            {"id": "HDFC", "name": "HDFC Bank Ltd", "code": "HDFC"},
            {"id": "AXIS", "name": "Axis Bank Ltd", "code": "AXIS"},
        ],
        "supported_account_types": ["savings", "current", "deposit"],
        "auth_method": "consent_handle",
        "consent_capabilities": {"periodic_fetch": True, "one_time_fetch": True, "max_validity_days": 180},
        "data_capabilities": ["PROFILE", "SUMMARY", "TRANSACTIONS"],
        "historical_days_limit": 90,
        "sync_capabilities": {"scheduled": True, "manual": True},
        "status": ProviderStatus.SANDBOX_ONLY.value,
        "is_sandbox": True,
        "docs_reference": "https://www.onemoney.in/developer",
        "config_status": "sandbox_ready",
        "provider_metadata": {"description": "Licensed NBFC-AA provider for financial information sharing."},
    },
    {
        "provider_code": "FINVU_AA",
        "name": "Finvu (Cookiejar Technologies)",
        "category": ProviderCategory.ACCOUNT_AGGREGATOR.value,
        "country": "IN",
        "supported_institutions": [
            {"id": "HDFC", "name": "HDFC Bank Ltd", "code": "HDFC"},
            {"id": "ICICI", "name": "ICICI Bank Ltd", "code": "ICICI"},
            {"id": "CANARA", "name": "Canara Bank", "code": "CANARA"},
        ],
        "supported_account_types": ["savings", "current", "deposit"],
        "auth_method": "consent_handle",
        "consent_capabilities": {"periodic_fetch": True, "one_time_fetch": True, "max_validity_days": 180},
        "data_capabilities": ["PROFILE", "SUMMARY", "TRANSACTIONS"],
        "historical_days_limit": 90,
        "sync_capabilities": {"scheduled": True, "manual": True},
        "status": ProviderStatus.SANDBOX_ONLY.value,
        "is_sandbox": True,
        "docs_reference": "https://finvu.in/docs",
        "config_status": "sandbox_ready",
        "provider_metadata": {"description": "Licensed NBFC-AA provider for ReBIT standard financial data consent."},
    },
    {
        "provider_code": "PLAID_US",
        "name": "Plaid International Gateway",
        "category": ProviderCategory.BANKING_API.value,
        "country": "US",
        "supported_institutions": [
            {"id": "CHASE", "name": "JPMorgan Chase", "code": "CHASE"},
            {"id": "BOA", "name": "Bank of America", "code": "BOA"},
        ],
        "supported_account_types": ["checking", "savings", "credit_card"],
        "auth_method": "oauth2",
        "consent_capabilities": {"periodic_fetch": True, "max_validity_days": 365},
        "data_capabilities": ["TRANSACTIONS", "BALANCES"],
        "historical_days_limit": 365,
        "sync_capabilities": {"scheduled": True, "manual": True},
        "status": ProviderStatus.DISABLED.value,
        "is_sandbox": True,
        "docs_reference": "https://plaid.com/docs",
        "config_status": "unconfigured",
        "provider_metadata": {"description": "International open banking provider for global expansion."},
    },
]


class FinancialProviderRegistry:
    """Registry maintaining active providers and resolving runtime adapter instances."""

    _adapters: Dict[str, FinancialProviderAdapter] = {
        "MOCK_SANDBOX_AA": MockSandboxAdapter(),
        "SETU_AA": IndiaAccountAggregatorAdapter(provider_code="SETU_AA"),
        "ONEMONEY_AA": IndiaAccountAggregatorAdapter(provider_code="ONEMONEY_AA"),
        "FINVU_AA": IndiaAccountAggregatorAdapter(provider_code="FINVU_AA"),
    }

    @classmethod
    def get_catalog(cls) -> List[Dict[str, Any]]:
        """Returns the full provider catalog."""
        return REGISTERED_PROVIDERS_CATALOG

    @classmethod
    def get_provider_definition(cls, provider_code: str) -> Optional[Dict[str, Any]]:
        """Finds provider definition by code."""
        code_upper = provider_code.upper()
        for p in REGISTERED_PROVIDERS_CATALOG:
            if p["provider_code"] == code_upper:
                return p
        return None

    @classmethod
    def get_adapter(cls, provider_code: str) -> FinancialProviderAdapter:
        """Resolves the appropriate adapter instance for a given provider code."""
        code_upper = provider_code.upper()
        if code_upper in cls._adapters:
            return cls._adapters[code_upper]
        # Default to mock sandbox adapter if unknown or test
        return cls._adapters["MOCK_SANDBOX_AA"]
