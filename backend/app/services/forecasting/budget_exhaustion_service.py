"""
Arthsavora Budget Exhaustion Prediction Service
Analyzes current budget utilization and spending pace to estimate period exhaustion dates.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.forecasting import calculate_budget_exhaustion
from app.repositories.budget_repository import BudgetRepository
from app.schemas.forecast_schema import BudgetExhaustionResponse


class BudgetExhaustionService:
    """Predicts when active budget allocations will be exhausted based on spending burn rate."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.budget_repo = BudgetRepository(db)

    async def get_exhaustion_estimates(
        self,
        workspace_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> BudgetExhaustionResponse:
        """Computes budget exhaustion dates across active workspace budgets and allocations."""
        as_of = as_of_date or date.today()
        budgets, _ = await self.budget_repo.list_budgets(workspace_id=workspace_id, status="active", limit=50)

        estimates: List[Dict[str, Any]] = []

        for b in budgets:
            # 1. Single aggregation query computing overall and category spend
            spend_data = await self.budget_repo.calculate_actual_spending_for_budget(
                workspace_id=workspace_id,
                start_date=b.start_date,
                end_date=min(as_of, b.end_date),
                currency=b.currency or "INR",
            )
            actual_spend = spend_data.get("spent_paise", 0)
            cat_spend_map = spend_data.get("category_spending", {})

            overall_est = calculate_budget_exhaustion(
                budget_id=str(b.id),
                budget_name=b.name,
                total_allocated_paise=b.total_allocated_paise,
                current_spend_paise=actual_spend,
                period_start=b.start_date,
                period_end=b.end_date,
                as_of_date=as_of,
                category_id=None,
                category_name="Overall Budget",
            )

            estimates.append({
                "budget_id": overall_est.budget_id,
                "budget_name": overall_est.budget_name,
                "category_id": overall_est.category_id,
                "category_name": overall_est.category_name,
                "total_allocated_paise": overall_est.total_allocated_paise,
                "total_allocated": Decimal(overall_est.total_allocated_paise) / Decimal("100.0000"),
                "current_spend_paise": overall_est.current_spend_paise,
                "current_spend": Decimal(overall_est.current_spend_paise) / Decimal("100.0000"),
                "remaining_paise": overall_est.remaining_paise,
                "remaining": Decimal(overall_est.remaining_paise) / Decimal("100.0000"),
                "burn_rate_daily_paise": overall_est.burn_rate_daily_paise,
                "burn_rate_daily": Decimal(overall_est.burn_rate_daily_paise) / Decimal("100.0000"),
                "utilization_pct": overall_est.utilization_pct,
                "estimated_exhaustion_date": overall_est.estimated_exhaustion_date,
                "days_to_exhaustion": overall_est.days_to_exhaustion,
                "status": overall_est.status,
            })

            # 2. Category-level allocation estimates
            if b.allocations:
                for alloc in b.allocations:
                    cat_spend = cat_spend_map.get(alloc.category_id, 0)
                    cat_name = alloc.category.name if alloc.category else "Category"

                    cat_est = calculate_budget_exhaustion(
                        budget_id=str(b.id),
                        budget_name=b.name,
                        total_allocated_paise=alloc.allocated_amount_paise,
                        current_spend_paise=cat_spend,
                        period_start=b.start_date,
                        period_end=b.end_date,
                        as_of_date=as_of,
                        category_id=str(alloc.category_id),
                        category_name=cat_name,
                    )

                    estimates.append({
                        "budget_id": cat_est.budget_id,
                        "budget_name": cat_est.budget_name,
                        "category_id": cat_est.category_id,
                        "category_name": cat_est.category_name,
                        "total_allocated_paise": cat_est.total_allocated_paise,
                        "total_allocated": Decimal(cat_est.total_allocated_paise) / Decimal("100.0000"),
                        "current_spend_paise": cat_est.current_spend_paise,
                        "current_spend": Decimal(cat_est.current_spend_paise) / Decimal("100.0000"),
                        "remaining_paise": cat_est.remaining_paise,
                        "remaining": Decimal(cat_est.remaining_paise) / Decimal("100.0000"),
                        "burn_rate_daily_paise": cat_est.burn_rate_daily_paise,
                        "burn_rate_daily": Decimal(cat_est.burn_rate_daily_paise) / Decimal("100.0000"),
                        "utilization_pct": cat_est.utilization_pct,
                        "estimated_exhaustion_date": cat_est.estimated_exhaustion_date,
                        "days_to_exhaustion": cat_est.days_to_exhaustion,
                        "status": cat_est.status,
                    })

        return BudgetExhaustionResponse(
            workspace_id=workspace_id,
            as_of_date=as_of,
            estimates=estimates,
        )
