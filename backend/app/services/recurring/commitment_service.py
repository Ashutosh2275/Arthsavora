"""
Arthsavora Expected Cash-Flow Commitments & Recurring Analytics Service
Aggregates upcoming expected inflows, outflows, and normalized commitments across
defined time horizons (7, 30, 90 days) with strict actual-versus-expected separation.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recurring import normalize_cost_to_monthly_and_annual
from app.infrastructure.database.models.recurring import RecurringOccurrence
from app.repositories.recurring_repository import RecurringRepository
from app.schemas.recurring_schema import (
    CashFlowCommitmentsResponse,
    CommitmentBreakdownByType,
    OccurrenceResponse,
)


class CommitmentService:
    """Calculates forward-looking cash-flow commitments and recurring analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringRepository(db)

    async def get_commitments(
        self,
        workspace_id: uuid.UUID,
        window_days: int = 30,
        start_date: Optional[date] = None,
        as_of_date: Optional[date] = None,
    ) -> CashFlowCommitmentsResponse:
        """
        Derives forward-looking cash-flow commitments for the specified workspace.
        """
        start = start_date or as_of_date or date.today()
        end = start + timedelta(days=window_days)

        # Fetch active definitions to compute normalized run-rates
        active_defs = await self.repo.list_definitions(workspace_id=workspace_id, status="active", limit=500)
        active_subs = await self.repo.list_subscriptions(workspace_id=workspace_id, status="active", limit=500)

        total_norm_monthly_paise = 0
        total_norm_annual_paise = 0

        for d in active_defs:
            if d.direction == "outflow":
                m, a = normalize_cost_to_monthly_and_annual(
                    amount_paise=d.expected_amount_paise,
                    frequency=d.frequency,
                    cycle_interval=d.interval,
                )
                total_norm_monthly_paise += m
                total_norm_annual_paise += a

        # Fetch occurrences within window (excluding skipped/cancelled)
        occurrences = await self.repo.list_occurrences(
            workspace_id=workspace_id,
            start_date=start,
            end_date=end,
            limit=200,
        )

        inflow_paise = 0
        outflow_paise = 0

        category_breakdown_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "amount_paise": 0})
        type_breakdown_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "amount_paise": 0})

        upcoming_list: List[OccurrenceResponse] = []

        for occ in occurrences:
            if occ.status in ("skipped", "cancelled"):
                continue

            defn = occ.recurring_definition
            direction = defn.direction if defn else "outflow"
            amt = occ.expected_amount_paise

            if direction == "inflow":
                inflow_paise += amt
            else:
                outflow_paise += amt

            # Classify commitment type
            name_lower = (defn.name if defn else "").lower()
            cat_name = defn.category.name if (defn and defn.category) else "General"

            if "rent" in name_lower:
                type_name = "Rent & Housing"
            elif any(w in name_lower for w in ("emi", "loan", "mortgage")):
                type_name = "Loan & EMI"
            elif any(w in name_lower for w in ("electricity", "water", "gas", "internet", "utility", "bill")):
                type_name = "Utilities"
            elif any(w in name_lower for w in ("insurance", "lic", "policy")):
                type_name = "Insurance"
            elif any(w in name_lower for w in ("salary", "stipend", "bonus", "dividend")):
                type_name = "Income"
            elif "subscription" in name_lower or (defn and defn.description and "subscription" in defn.description.lower()):
                type_name = "Subscriptions"
            else:
                type_name = "Other Commitments"

            category_breakdown_map[cat_name]["count"] += 1
            category_breakdown_map[cat_name]["amount_paise"] += amt

            type_breakdown_map[type_name]["count"] += 1
            type_breakdown_map[type_name]["amount_paise"] += amt

            upcoming_list.append(
                OccurrenceResponse(
                    id=occ.id,
                    workspace_id=occ.workspace_id,
                    recurring_definition_id=occ.recurring_definition_id,
                    recurring_name=defn.name if defn else None,
                    direction=direction,
                    expected_date=occ.expected_date,
                    expected_amount_paise=occ.expected_amount_paise,
                    expected_amount=occ.expected_amount,
                    currency=occ.currency,
                    status=occ.status,
                    matched_transaction_id=occ.matched_transaction_id,
                    matched_amount_paise=occ.matched_amount_paise,
                    matched_amount=Decimal(occ.matched_amount_paise) / Decimal("100.0000") if occ.matched_amount_paise else None,
                    amount_variance_paise=occ.amount_variance_paise,
                    match_confidence=occ.match_confidence,
                    notes=occ.notes,
                    generated_at=occ.generated_at,
                    confirmed_at=occ.confirmed_at,
                    updated_at=occ.updated_at,
                )
            )

        cat_list = [
            {
                "category_name": cat,
                "count": data["count"],
                "total_amount_paise": data["amount_paise"],
                "total_amount": Decimal(data["amount_paise"]) / Decimal("100.0000"),
            }
            for cat, data in sorted(category_breakdown_map.items(), key=lambda x: x[1]["amount_paise"], reverse=True)
        ]

        type_list = [
            CommitmentBreakdownByType(
                type_name=t,
                count=data["count"],
                total_amount_paise=data["amount_paise"],
                total_amount=Decimal(data["amount_paise"]) / Decimal("100.0000"),
            )
            for t, data in sorted(type_breakdown_map.items(), key=lambda x: x[1]["amount_paise"], reverse=True)
        ]

        net_commitment_paise = inflow_paise - outflow_paise

        return CashFlowCommitmentsResponse(
            workspace_id=workspace_id,
            window_days=window_days,
            start_date=start,
            end_date=end,
            total_expected_inflow_paise=inflow_paise,
            total_expected_inflow=Decimal(inflow_paise) / Decimal("100.0000"),
            total_expected_outflow_paise=outflow_paise,
            total_expected_outflow=Decimal(outflow_paise) / Decimal("100.0000"),
            net_commitment_paise=net_commitment_paise,
            net_commitment=Decimal(net_commitment_paise) / Decimal("100.0000"),
            active_recurring_count=len(active_defs),
            active_subscription_count=len(active_subs),
            normalized_monthly_expenses_paise=total_norm_monthly_paise,
            normalized_monthly_expenses=Decimal(total_norm_monthly_paise) / Decimal("100.0000"),
            normalized_annual_expenses_paise=total_norm_annual_paise,
            normalized_annual_expenses=Decimal(total_norm_annual_paise) / Decimal("100.0000"),
            commitments_by_category=cat_list,
            commitments_by_type=type_list,
            upcoming_occurrences=upcoming_list,
        )
