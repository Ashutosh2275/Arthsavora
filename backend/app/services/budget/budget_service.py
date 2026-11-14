"""
Arthsavora Budget Application Service
Orchestrates personal budgets, category spending ceilings, deterministic progress evaluation,
historical revision tracking, idempotent threshold alert triggers, and period rollovers.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.domain.budget import (
    BudgetType,
    BudgetWarningState,
    RecurrenceInterval,
    calculate_budget_progress,
    calculate_linear_projection,
    calculate_period_progress,
    generate_next_period_bounds,
)
from app.domain.exceptions import BusinessRuleViolationError
from app.infrastructure.database.models.budget import (
    Budget,
    BudgetAllocation,
    BudgetRevision,
    BudgetAlert,
)
from app.repositories.budget_repository import BudgetRepository


class BudgetService:
    """Service layer orchestrating personal budgeting, category limits, and spending controls."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BudgetRepository(session)

    def _validate_date_range(self, start_date: date, end_date: date) -> None:
        """Validates that date bounds are strictly ordered."""
        if start_date > end_date:
            raise BusinessRuleViolationError(
                rule_name="INVALID_BUDGET_PERIOD",
                message=f"Budget start date ({start_date}) cannot be after end date ({end_date}).",
            )

    def _validate_currency(self, currency: str) -> str:
        """Normalizes and validates ISO currency code."""
        c = currency.strip().upper()
        if len(c) != 3 or not c.isalpha():
            raise BusinessRuleViolationError(
                rule_name="INVALID_CURRENCY",
                message=f"Currency '{currency}' must be a valid 3-letter ISO code.",
            )
        return c

    async def create_budget(
        self,
        workspace_id: uuid.UUID,
        name: str,
        start_date: date,
        end_date: date,
        total_allocated_paise: int,
        budget_type: str = "monthly",
        currency: str = "INR",
        recurrence_interval: str = "monthly",
        created_by_id: Optional[uuid.UUID] = None,
        allocations: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Budget:
        """
        Creates a new budget with optional initial category allocations.
        Records initial budget revision.
        """
        self._validate_date_range(start_date, end_date)
        valid_curr = self._validate_currency(currency)

        if total_allocated_paise < 0:
            raise BusinessRuleViolationError(
                rule_name="INVALID_ALLOCATION_AMOUNT",
                message="Total allocated budget amount cannot be negative.",
            )

        budget = Budget(
            workspace_id=workspace_id,
            name=name.strip(),
            budget_type=budget_type,
            currency=valid_curr,
            start_date=start_date,
            end_date=end_date,
            total_allocated_paise=total_allocated_paise,
            total_allocated=Decimal(total_allocated_paise) / Decimal(100),
            recurrence_interval=recurrence_interval,
            status="active",
            created_by_id=created_by_id,
            settings=settings or {},
        )
        self.session.add(budget)
        await self.session.flush()

        # Record initial revision
        await self.repo.record_revision(
            budget_id=budget.id,
            workspace_id=workspace_id,
            revision_type="created",
            previous_amount_paise=None,
            new_amount_paise=total_allocated_paise,
            change_reason="Initial budget created",
            changed_by_id=created_by_id,
        )

        # Process initial allocations if provided
        if allocations:
            for item in allocations:
                cat_id = item["category_id"]
                if isinstance(cat_id, str):
                    cat_id = uuid.UUID(cat_id)
                amt_paise = item["allocated_amount_paise"]
                warn_pct = item.get("warning_threshold_percentage", 80)
                notes = item.get("notes")

                alloc = BudgetAllocation(
                    budget_id=budget.id,
                    workspace_id=workspace_id,
                    category_id=cat_id,
                    allocated_amount_paise=amt_paise,
                    allocated_amount=Decimal(amt_paise) / Decimal(100),
                    warning_threshold_percentage=warn_pct,
                    status="active",
                    notes=notes,
                )
                self.session.add(alloc)
                await self.session.flush()

                await self.repo.record_revision(
                    budget_id=budget.id,
                    workspace_id=workspace_id,
                    allocation_id=alloc.id,
                    category_id=cat_id,
                    revision_type="allocation_created",
                    previous_amount_paise=None,
                    new_amount_paise=amt_paise,
                    change_reason="Initial allocation",
                    changed_by_id=created_by_id,
                )

        await self.session.flush()
        return await self.get_budget(budget.id, workspace_id)

    async def get_budget(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Budget:
        """Retrieves budget or raises 404."""
        budget = await self.repo.get_budget_with_allocations(budget_id, workspace_id)
        if not budget:
            raise NotFoundException(f"Budget '{budget_id}' not found in workspace.")
        return budget

    async def list_budgets(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Budget]:
        """Lists budgets for the workspace."""
        items, _ = await self.repo.list_budgets(
            workspace_id=workspace_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return items

    async def update_budget(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: Optional[str] = None,
        total_allocated_paise: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        recurrence_interval: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        revision_reason: Optional[str] = None,
        changed_by_id: Optional[uuid.UUID] = None,
    ) -> Budget:
        """Updates top-level budget attributes and records an audit revision."""
        budget = await self.get_budget(budget_id, workspace_id)

        if start_date is not None or end_date is not None:
            new_s = start_date or budget.start_date
            new_e = end_date or budget.end_date
            self._validate_date_range(new_s, new_e)
            budget.start_date = new_s
            budget.end_date = new_e

        if name is not None:
            budget.name = name.strip()

        if recurrence_interval is not None:
            budget.recurrence_interval = recurrence_interval

        if total_allocated_paise is not None:
            if total_allocated_paise < 0:
                raise BusinessRuleViolationError(
                    rule_name="INVALID_ALLOCATION_AMOUNT",
                    message="Total allocated budget amount cannot be negative.",
                )
            prev = budget.total_allocated_paise
            budget.total_allocated_paise = total_allocated_paise
            budget.total_allocated = Decimal(total_allocated_paise) / Decimal(100)

            await self.repo.record_revision(
                budget_id=budget.id,
                workspace_id=workspace_id,
                revision_type="budget_updated",
                previous_amount_paise=prev,
                new_amount_paise=total_allocated_paise,
                change_reason=revision_reason or "Budget overall cap updated",
                changed_by_id=changed_by_id,
            )

        if status is not None:
            budget.status = status

        if settings is not None:
            budget.settings = {**budget.settings, **settings}

        await self.session.flush()
        return await self.get_budget(budget.id, workspace_id)

    async def delete_budget(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        reason: Optional[str] = None,
        deleted_by_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Soft-deletes/archives a budget and logs the revision."""
        budget = await self.get_budget(budget_id, workspace_id)
        budget.is_deleted = True
        budget.status = "archived"

        await self.repo.record_revision(
            budget_id=budget.id,
            workspace_id=workspace_id,
            revision_type="budget_archived",
            previous_amount_paise=budget.total_allocated_paise,
            new_amount_paise=0,
            change_reason=reason or "Budget archived by user",
            changed_by_id=deleted_by_id,
        )
        await self.session.flush()

    async def add_allocation(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        category_id: uuid.UUID,
        allocated_amount_paise: int,
        warning_threshold_percentage: int = 80,
        notes: Optional[str] = None,
        revision_reason: Optional[str] = None,
        changed_by_id: Optional[uuid.UUID] = None,
    ) -> BudgetAllocation:
        """Adds a category allocation to a budget."""
        budget = await self.get_budget(budget_id, workspace_id)

        if allocated_amount_paise < 0:
            raise BusinessRuleViolationError(
                rule_name="INVALID_ALLOCATION_AMOUNT",
                message="Category allocation amount cannot be negative.",
            )

        existing = await self.repo.get_allocation_by_category(budget.id, category_id)
        if existing:
            raise BusinessRuleViolationError(
                rule_name="DUPLICATE_CATEGORY_ALLOCATION",
                message=f"Category '{category_id}' is already allocated in this budget. Use update instead.",
            )

        alloc = BudgetAllocation(
            budget_id=budget.id,
            workspace_id=workspace_id,
            category_id=category_id,
            allocated_amount_paise=allocated_amount_paise,
            allocated_amount=Decimal(allocated_amount_paise) / Decimal(100),
            warning_threshold_percentage=warning_threshold_percentage,
            status="active",
            notes=notes,
        )
        self.session.add(alloc)
        await self.session.flush()

        await self.repo.record_revision(
            budget_id=budget.id,
            workspace_id=workspace_id,
            allocation_id=alloc.id,
            category_id=category_id,
            revision_type="allocation_added",
            previous_amount_paise=None,
            new_amount_paise=allocated_amount_paise,
            change_reason=revision_reason or "Added category allocation",
            changed_by_id=changed_by_id,
        )
        await self.session.flush()
        return alloc

    async def update_allocation(
        self,
        budget_id: uuid.UUID,
        allocation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        allocated_amount_paise: Optional[int] = None,
        warning_threshold_percentage: Optional[int] = None,
        notes: Optional[str] = None,
        revision_reason: Optional[str] = None,
        changed_by_id: Optional[uuid.UUID] = None,
    ) -> BudgetAllocation:
        """Updates an existing category allocation and logs the revision."""
        budget = await self.get_budget(budget_id, workspace_id)
        alloc = await self.repo.get_allocation_by_id(allocation_id, budget_id, workspace_id)
        if not alloc:
            raise NotFoundException(f"Allocation '{allocation_id}' not found in budget.")

        prev_paise = alloc.allocated_amount_paise

        if allocated_amount_paise is not None:
            if allocated_amount_paise < 0:
                raise BusinessRuleViolationError(
                    rule_name="INVALID_ALLOCATION_AMOUNT",
                    message="Category allocation amount cannot be negative.",
                )
            alloc.allocated_amount_paise = allocated_amount_paise
            alloc.allocated_amount = Decimal(allocated_amount_paise) / Decimal(100)

        if warning_threshold_percentage is not None:
            alloc.warning_threshold_percentage = warning_threshold_percentage

        if notes is not None:
            alloc.notes = notes

        await self.repo.record_revision(
            budget_id=budget.id,
            workspace_id=workspace_id,
            allocation_id=alloc.id,
            category_id=alloc.category_id,
            revision_type="allocation_updated",
            previous_amount_paise=prev_paise,
            new_amount_paise=alloc.allocated_amount_paise,
            change_reason=revision_reason or "Adjusted category limit",
            changed_by_id=changed_by_id,
        )
        await self.session.flush()
        return alloc

    async def remove_allocation(
        self,
        budget_id: uuid.UUID,
        allocation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        revision_reason: Optional[str] = None,
        changed_by_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Removes a category allocation from a budget."""
        budget = await self.get_budget(budget_id, workspace_id)
        alloc = await self.repo.get_allocation_by_id(allocation_id, budget_id, workspace_id)
        if not alloc:
            raise NotFoundException(f"Allocation '{allocation_id}' not found in budget.")

        prev_paise = alloc.allocated_amount_paise
        cat_id = alloc.category_id

        await self.session.delete(alloc)
        await self.repo.record_revision(
            budget_id=budget.id,
            workspace_id=workspace_id,
            allocation_id=allocation_id,
            category_id=cat_id,
            revision_type="allocation_removed",
            previous_amount_paise=prev_paise,
            new_amount_paise=0,
            change_reason=revision_reason or "Category allocation removed",
            changed_by_id=changed_by_id,
        )
        await self.session.flush()

    async def list_revisions(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> List[BudgetRevision]:
        """Lists audit revisions for a budget."""
        # Ensure budget exists in workspace first
        await self.get_budget(budget_id, workspace_id)
        return await self.repo.list_revisions(budget_id, workspace_id, limit=limit)

    async def list_alerts(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> List[BudgetAlert]:
        """Lists triggered threshold alerts for a budget."""
        await self.get_budget(budget_id, workspace_id)
        return await self.repo.list_alerts(workspace_id, budget_id=budget_id, limit=limit)

    async def get_budget_progress(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        as_of_date: Optional[date] = None,
        evaluate_alerts: bool = True,
    ) -> Dict[str, Any]:
        """
        Derives complete budget progress:
        - Actual overall spending vs allocated overall cap
        - Category-by-category allocation spending, utilization, and warning states
        - Unallocated spending capacity
        - Temporal progress through period
        - Deterministic linear run-rate projection
        - Idempotent threshold alert evaluation (50%, 75%, 80%, 90%, 100%)
        """
        budget = await self.get_budget(budget_id, workspace_id)
        current_date = as_of_date or date.today()

        # Query authoritative actual spending
        spending_data = await self.repo.calculate_actual_spending_for_budget(
            workspace_id=workspace_id,
            start_date=budget.start_date,
            end_date=budget.end_date,
            currency=budget.currency,
        )

        overall_spent_paise = spending_data["overall_spent_paise"]
        cat_spend_map = spending_data["category_spending_map"]

        # 1. Overall Budget Progress
        overall_metrics = calculate_budget_progress(
            allocated_amount_paise=budget.total_allocated_paise,
            actual_spent_paise=overall_spent_paise,
            warning_threshold_pct=80,
        )

        # 2. Temporal Period Progress
        period_metrics = calculate_period_progress(
            start_date=budget.start_date,
            end_date=budget.end_date,
            as_of_date=current_date,
        )

        # 3. Deterministic Linear Run-Rate Projection
        projection = calculate_linear_projection(
            allocated_amount_paise=budget.total_allocated_paise,
            actual_spent_paise=overall_spent_paise,
            days_elapsed=period_metrics.days_elapsed,
            total_days=period_metrics.total_days,
        )

        # 4. Category Allocations Progress
        total_category_allocated_paise = 0
        allocation_items = []
        new_alerts_count = 0

        for alloc in budget.allocations:
            total_category_allocated_paise += alloc.allocated_amount_paise
            spent_entry = cat_spend_map.get(alloc.category_id, {"spent_paise": 0, "transaction_count": 0})
            spent_paise = spent_entry["spent_paise"]

            cat_progress = calculate_budget_progress(
                allocated_amount_paise=alloc.allocated_amount_paise,
                actual_spent_paise=spent_paise,
                warning_threshold_pct=alloc.warning_threshold_percentage,
            )

            # Idempotent category alert checks if requested
            if evaluate_alerts:
                alert_created = await self._evaluate_and_trigger_alerts(
                    budget_id=budget.id,
                    workspace_id=workspace_id,
                    allocation_id=alloc.id,
                    category_id=alloc.category_id,
                    allocated_paise=alloc.allocated_amount_paise,
                    spent_paise=spent_paise,
                    utilization=cat_progress.utilization_percentage,
                    warning_threshold=alloc.warning_threshold_percentage,
                    entity_label=alloc.category.name if alloc.category else "Category",
                )
                if alert_created:
                    new_alerts_count += 1

            allocation_items.append({
                "allocation_id": alloc.id,
                "category_id": alloc.category_id,
                "category_name": alloc.category.name if alloc.category else "Unknown",
                "category_color": getattr(alloc.category, "color", None) if alloc.category else "#6366f1",
                "allocated_paise": alloc.allocated_amount_paise,
                "allocated_amount": Decimal(alloc.allocated_amount_paise) / Decimal(100),
                "spent_paise": spent_paise,
                "spent_amount": Decimal(spent_paise) / Decimal(100),
                "remaining_paise": cat_progress.remaining_amount_paise,
                "remaining_amount": cat_progress.remaining_amount,
                "utilization_percentage": cat_progress.utilization_percentage,
                "overspent": cat_progress.is_overspent,
                "warning_state": cat_progress.warning_state.value,
                "warning_threshold_percentage": alloc.warning_threshold_percentage,
            })

        # Overall budget alert check
        if evaluate_alerts:
            ov_alert = await self._evaluate_and_trigger_alerts(
                budget_id=budget.id,
                workspace_id=workspace_id,
                allocation_id=None,
                category_id=None,
                allocated_paise=budget.total_allocated_paise,
                spent_paise=overall_spent_paise,
                utilization=overall_metrics.utilization_percentage,
                warning_threshold=80,
                entity_label=budget.name,
            )
            if ov_alert:
                new_alerts_count += 1

        unallocated_paise = max(0, budget.total_allocated_paise - total_category_allocated_paise)

        return {
            "budget_id": budget.id,
            "name": budget.name,
            "currency": budget.currency,
            "start_date": budget.start_date,
            "end_date": budget.end_date,
            "as_of_date": current_date,
            "total_allocated_paise": overall_metrics.allocated_amount_paise,
            "total_allocated_amount": overall_metrics.allocated_amount,
            "total_spent_paise": overall_metrics.actual_spent_paise,
            "total_spent_amount": overall_metrics.actual_spent,
            "remaining_paise": overall_metrics.remaining_amount_paise,
            "remaining_amount": overall_metrics.remaining_amount,
            "utilization_percentage": overall_metrics.utilization_percentage,
            "overspent": overall_metrics.is_overspent,
            "warning_state": overall_metrics.warning_state.value,
            "period_days": period_metrics.total_days,
            "elapsed_days": period_metrics.days_elapsed,
            "remaining_days": period_metrics.days_remaining,
            "period_elapsed_percentage": period_metrics.period_progress_percentage,
            "linear_projection": {
                "days_in_period": period_metrics.total_days,
                "elapsed_days": period_metrics.days_elapsed,
                "remaining_days": period_metrics.days_remaining,
                "daily_run_rate_paise": projection.average_daily_spend_paise,
                "daily_run_rate": projection.average_daily_spend,
                "projected_period_end_spend_paise": projection.projected_period_end_spend_paise,
                "projected_period_end_spend": projection.projected_period_end_spend,
                "projected_variance_paise": projection.projected_variance_paise,
                "projected_variance": projection.projected_variance,
                "projected_overspent": projection.is_projected_to_exceed,
                "methodology": "linear_extrapolation",
                "assumptions": projection.confidence_disclosure,
            },
            "allocations": allocation_items,
            "unallocated_capacity_paise": unallocated_paise,
            "unallocated_capacity_amount": Decimal(unallocated_paise) / Decimal(100),
            "new_alerts_triggered": new_alerts_count,
        }

    async def _evaluate_and_trigger_alerts(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        allocation_id: Optional[uuid.UUID],
        category_id: Optional[uuid.UUID],
        allocated_paise: int,
        spent_paise: int,
        utilization: float,
        warning_threshold: int,
        entity_label: str,
    ) -> bool:
        """Evaluates threshold crossings (warning_threshold%, 100%) and records idempotent alerts without spamming."""
        if allocated_paise <= 0:
            return False

        created = False
        # 1. Warning Threshold Crossing (e.g. 80%)
        if utilization >= warning_threshold:
            msg = f"{entity_label} has reached {utilization:.1f}% utilization ({warning_threshold}% warning threshold)."
            alert = await self.repo.record_alert_idempotent(
                budget_id=budget_id,
                workspace_id=workspace_id,
                allocation_id=allocation_id,
                category_id=category_id,
                alert_type="threshold_crossed",
                threshold_percentage=warning_threshold,
                actual_spent_paise=spent_paise,
                allocated_amount_paise=allocated_paise,
                utilization_percentage=Decimal(str(round(utilization, 2))),
                message=msg,
            )
            if alert:
                created = True

        # 2. Budget Exhausted / Exceeded (100%+)
        if utilization >= 100.0:
            overspent_paise = max(0, spent_paise - allocated_paise)
            if overspent_paise > 0:
                msg = f"{entity_label} has exceeded its budget by ₹{Decimal(overspent_paise) / Decimal(100):,.2f} ({utilization:.1f}% utilization)."
                alert_type = "budget_exceeded"
            else:
                msg = f"{entity_label} budget is 100% exhausted."
                alert_type = "budget_exhausted"

            alert_100 = await self.repo.record_alert_idempotent(
                budget_id=budget_id,
                workspace_id=workspace_id,
                allocation_id=allocation_id,
                category_id=category_id,
                alert_type=alert_type,
                threshold_percentage=100,
                actual_spent_paise=spent_paise,
                allocated_amount_paise=allocated_paise,
                utilization_percentage=Decimal(str(round(utilization, 2))),
                message=msg,
            )
            if alert_100:
                created = True

        return created

    async def rollover_budget(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        new_start_date: Optional[date] = None,
        new_end_date: Optional[date] = None,
        adjust_allocation_paise: Optional[int] = None,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> Budget:
        """
        Creates the next cycle of a budget idempotently.
        Preserves previous period historical records and carries forward category limits.
        """
        current_budget = await self.get_budget(budget_id, workspace_id)

        if new_start_date and new_end_date:
            next_start = new_start_date
            next_end = new_end_date
        else:
            interval_str = current_budget.recurrence_interval or "monthly"
            if interval_str == "none":
                interval_str = "monthly"
            interval_enum = RecurrenceInterval(interval_str)
            next_start, next_end = generate_next_period_bounds(
                current_budget.start_date,
                current_budget.end_date,
                interval_enum,
            )

        total_paise = adjust_allocation_paise if adjust_allocation_paise is not None else current_budget.total_allocated_paise

        allocations_to_carry = []
        for alloc in current_budget.allocations:
            allocations_to_carry.append({
                "category_id": alloc.category_id,
                "allocated_amount_paise": alloc.allocated_amount_paise,
                "warning_threshold_percentage": alloc.warning_threshold_percentage,
                "notes": alloc.notes,
            })

        new_budget = await self.create_budget(
            workspace_id=workspace_id,
            name=current_budget.name,
            start_date=next_start,
            end_date=next_end,
            total_allocated_paise=total_paise,
            budget_type=current_budget.budget_type,
            currency=current_budget.currency,
            recurrence_interval=current_budget.recurrence_interval,
            created_by_id=created_by_id,
            allocations=allocations_to_carry,
            settings=current_budget.settings,
        )
        return new_budget
