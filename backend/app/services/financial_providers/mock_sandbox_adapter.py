"""
Arthsavora Mock Sandbox Financial Provider Adapter
Provides deterministic, zero-network-dependency simulation of an Account Aggregator (AA)
and Open Banking data provider for testing, sandbox verification, and local development.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from app.domain.financial_connection import (
    ConsentStatus,
    NormalizedAccountVO,
    NormalizedTransactionVO,
)
from app.services.financial_providers.base import FinancialProviderAdapter


class MockSandboxAdapter(FinancialProviderAdapter):
    """Deterministic simulation adapter supporting Indian banking institutions."""

    PROVIDER_CODE = "MOCK_SANDBOX_AA"

    @property
    def provider_code(self) -> str:
        return self.PROVIDER_CODE

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
        handle = f"MOCK_CONSENT_{uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)
        valid_to = now + timedelta(days=valid_days)

        return {
            "provider_consent_handle": handle,
            "authorization_url": f"https://sandbox.arthsavora.internal/mock-aa/consent?handle={handle}",
            "valid_from": now,
            "valid_to": valid_to,
            "raw_response": {
                "ConsentHandle": handle,
                "status": "INITIATED",
                "purpose": purpose,
                "dataCategories": data_categories,
                "institutionId": institution_id,
            },
        }

    async def check_consent_status(
        self,
        provider_consent_handle: str,
    ) -> Dict[str, Any]:
        # In sandbox, handles ending in '_REJECTED' or '_EXPIRED' simulate alternative states
        if provider_consent_handle.endswith("_REJECTED"):
            status = ConsentStatus.REJECTED.value
        elif provider_consent_handle.endswith("_EXPIRED"):
            status = ConsentStatus.EXPIRED.value
        else:
            status = ConsentStatus.ACTIVE.value

        return {
            "status": status,
            "raw_artefact": {
                "consentId": f"ARTEFACT_{provider_consent_handle}",
                "status": status,
                "signature": "SHA256withRSA:MOCK_DIGITAL_SIGNATURE_ARTHSAVORA_SANDBOX",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def revoke_consent(
        self,
        provider_consent_handle: str,
        reason: Optional[str] = None,
    ) -> bool:
        return True

    async def discover_accounts(
        self,
        provider_consent_handle: str,
        institution_id: str,
    ) -> List[NormalizedAccountVO]:
        inst_upper = institution_id.upper()
        inst_name = {
            "HDFC": "HDFC Bank Ltd",
            "SBI": "State Bank of India",
            "ICICI": "ICICI Bank Ltd",
            "AXIS": "Axis Bank Ltd",
        }.get(inst_upper, f"{institution_id} Bank")

        now = datetime.now(timezone.utc)
        acc_1 = NormalizedAccountVO(
            provider_account_id=f"ACC_{inst_upper}_SAVINGS_001",
            fip_id=f"FIP_{inst_upper}",
            institution_name=inst_name,
            masked_account_number="••••4289",
            account_type="savings",
            currency="INR",
            current_balance_paise=25400000,  # ₹2,54,000.00
            available_balance_paise=25000000,
            balance_as_of=now,
            account_holder_name="Arthsavora Test User",
            metadata={"branch": "Koramangala, Bangalore", "ifsc": f"{inst_upper}0001234"},
        )

        acc_2 = NormalizedAccountVO(
            provider_account_id=f"ACC_{inst_upper}_CURRENT_002",
            fip_id=f"FIP_{inst_upper}",
            institution_name=inst_name,
            masked_account_number="••••8812",
            account_type="current",
            currency="INR",
            current_balance_paise=78500000,  # ₹7,85,000.00
            available_balance_paise=78500000,
            balance_as_of=now,
            account_holder_name="Arthsavora Commercial Ventures",
            metadata={"branch": "BKC, Mumbai", "ifsc": f"{inst_upper}0005678"},
        )

        return [acc_1, acc_2]

    async def fetch_transactions(
        self,
        provider_consent_handle: str,
        provider_account_id: str,
        from_date: date,
        to_date: date,
        cursor: Optional[str] = None,
    ) -> Tuple[List[NormalizedTransactionVO], Optional[str]]:
        today = date.today()
        # Generates deterministic financial transactions tailored to the account
        tx1 = NormalizedTransactionVO(
            external_transaction_id=f"TXN_{provider_account_id}_001",
            amount_paise=5000000,  # ₹50,000.00
            direction="inflow",
            transaction_date=today - timedelta(days=5),
            description="NEFT CR - TECH CLIENT CONSULTING SERVICES",
            merchant_name="Client Services",
            status="posted",
            reference_number="NEFT20261114001",
            category_code="INCOME_CONSULTING",
        )
        tx2 = NormalizedTransactionVO(
            external_transaction_id=f"TXN_{provider_account_id}_002",
            amount_paise=125000,  # ₹1,250.00
            direction="outflow",
            transaction_date=today - timedelta(days=3),
            description="UPI/DR/SWIGGY/ORDER_982312/swiggy@icici",
            merchant_name="Swiggy",
            status="posted",
            reference_number="UPI20261116002",
            category_code="FOOD_DINING",
        )
        tx3 = NormalizedTransactionVO(
            external_transaction_id=f"TXN_{provider_account_id}_003",
            amount_paise=450000,  # ₹4,500.00
            direction="outflow",
            transaction_date=today - timedelta(days=1),
            description="ACH DR - AIRTEL BROADBAND AND FIBER",
            merchant_name="Airtel",
            status="posted",
            reference_number="ACH20261118003",
            category_code="UTILITIES_INTERNET",
        )

        return [tx1, tx2, tx3], None

    async def fetch_balances(
        self,
        provider_consent_handle: str,
        provider_account_ids: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        result: Dict[str, Dict[str, Any]] = {}
        for acc_id in provider_account_ids:
            if "SAVINGS" in acc_id:
                result[acc_id] = {
                    "current_balance_paise": 25400000,
                    "available_balance_paise": 25000000,
                    "balance_as_of": now,
                }
            else:
                result[acc_id] = {
                    "current_balance_paise": 78500000,
                    "available_balance_paise": 78500000,
                    "balance_as_of": now,
                }
        return result
