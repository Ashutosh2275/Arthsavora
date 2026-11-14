"""
Arthsavora Personal Budgeting API Endpoints
Authenticated, workspace-scoped RESTful routes for personal budgets, category allocations,
deterministic spending progress evaluation, linear run-rate projections, audit revisions,
idempotent threshold alerts, and period rollovers.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.budget_schema import (
    AllocationCreateRequest,
    AllocationUpdateRequest,
    BudgetAllocationProgressResponse,
    BudgetAllocationResponse,
    BudgetAlertResponse,
    BudgetCreateRequest,
    BudgetDetailResponse,
    BudgetLinearProjectionResponse,
    BudgetProgressResponse,
    BudgetRevisionResponse,
    BudgetRolloverRequest,
    BudgetSummaryResponse,
    BudgetUpdateRequest,
)
from app.schemas.common import ApiResponse, PaginatedResponse
from app.services.budget.budget_service import BudgetService

router = APIRouter(tags=["Personal Budgeting & Spending Controls"])


def _map_allocation_response(alloc) -> BudgetAllocationResponse:
    cat_name = alloc.category.name if alloc.category else None
    cat_color = getattr(alloc.category, "color", None) if alloc.category else None
    return BudgetAllocationResponse(
        id=alloc.id,
        budget_id=alloc.budget_id,
        category_id=alloc.category_id,
        category_name=cat_name,
        category_color=cat_color,
        allocated_amount_paise=alloc.allocated_amount_paise,
        allocated_amount=alloc.allocated_amount,
        warning_threshold_percentage=alloc.warning_threshold_percentage,
        notes=alloc.notes,
        created_at=alloc.created_at,
        updated_at=alloc.updated_at,
    )


def _map_budget_summary(b) -> BudgetSummaryResponse:
    allocs = getattr(b, "allocations", [])
    return BudgetSummaryResponse(
        id=b.id,
        workspace_id=b.workspace_id,
        name=b.name,
        budget_type=b.budget_type,
        currency=b.currency,
        start_date=b.start_date,
        end_date=b.end_date,
        total_allocated_paise=b.total_allocated_paise,
        total_allocated=b.total_allocated,
        recurrence_interval=b.recurrence_interval,
        status=b.status,
        allocations_count=len(allocs),
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


def _map_budget_detail(b) -> BudgetDetailResponse:
    alloc_responses = [_map_allocation_response(a) for a in getattr(b, "allocations", [])]
    return BudgetDetailResponse(
        id=b.id,
        workspace_id=b.workspace_id,
        name=b.name,
        budget_type=b.budget_type,
        currency=b.currency,
        start_date=b.start_date,
        end_date=b.end_date,
        total_allocated_paise=b.total_allocated_paise,
        total_allocated=b.total_allocated,
        recurrence_interval=b.recurrence_interval,
        status=b.status,
        allocations_count=len(alloc_responses),
        created_at=b.created_at,
        updated_at=b.updated_at,
        allocations=alloc_responses,
        settings=b.settings or {},
    )


@router.get(
    "",
    response_model=ApiResponse[List[BudgetSummaryResponse]],
    summary="List Workspace Budgets",
)
async def list_budgets(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, archived, closed)"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves all budgets scoped to the current active workspace."""
    service = BudgetService(session)
    budgets = await service.list_budgets(workspace_id=context.workspace_id, status=status_filter)
    items = [_map_budget_summary(b) for b in budgets]
    return ApiResponse(data=items)


@router.post(
    "",
    response_model=ApiResponse[BudgetDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Personal Budget",
)
async def create_budget(
    payload: BudgetCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Creates a new budget with optional initial category allocations.
    Automatically initializes the immutable budget revision audit ledger.
    """
    service = BudgetService(session)
    raw_allocs = None
    if payload.allocations:
        raw_allocs = [a.model_dump() for a in payload.allocations]

    budget = await service.create_budget(
        workspace_id=context.workspace_id,
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_allocated_paise=payload.total_allocated_paise,
        budget_type=payload.budget_type,
        currency=payload.currency,
        recurrence_interval=payload.recurrence_interval,
        created_by_id=context.user.id,
        allocations=raw_allocs,
        settings=payload.settings,
    )
    # Reload with allocations and relationships
    full_budget = await service.get_budget(budget.id, context.workspace_id)
    return ApiResponse(data=_map_budget_detail(full_budget))


@router.get(
    "/{budget_id}",
    response_model=ApiResponse[BudgetDetailResponse],
    summary="Get Budget Details",
)
async def get_budget(
    budget_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves complete budget entity including category allocations."""
    service = BudgetService(session)
    budget = await service.get_budget(budget_id, context.workspace_id)
    return ApiResponse(data=_map_budget_detail(budget))


@router.patch(
    "/{budget_id}",
    response_model=ApiResponse[BudgetDetailResponse],
    summary="Update Budget",
)
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates budget boundaries and registers an immutable revision entry."""
    service = BudgetService(session)
    budget = await service.update_budget(
        budget_id=budget_id,
        workspace_id=context.workspace_id,
        name=payload.name,
        total_allocated_paise=payload.total_allocated_paise,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        recurrence_interval=payload.recurrence_interval,
        settings=payload.settings,
        revision_reason=payload.revision_reason,
        changed_by_id=context.user.id,
    )
    return ApiResponse(data=_map_budget_detail(budget))


@router.delete(
    "/{budget_id}",
    response_model=ApiResponse[dict],
    summary="Archive/Delete Budget",
)
async def delete_budget(
    budget_id: uuid.UUID,
    reason: Optional[str] = Query(None, description="Audit reason for deletion"),
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Archives/soft-deletes a budget and logs the revision."""
    service = BudgetService(session)
    await service.delete_budget(
        budget_id=budget_id,
        workspace_id=context.workspace_id,
        reason=reason,
        deleted_by_id=context.user.id,
    )
    return ApiResponse(data={"message": f"Budget {budget_id} archived successfully."})


@router.get(
    "/{budget_id}/progress",
    response_model=ApiResponse[BudgetProgressResponse],
    summary="Evaluate Budget Spending Progress & Projections",
)
async def get_budget_progress(
    budget_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None, description="Evaluation date (defaults to today)"),
    evaluate_alerts: bool = Query(True, description="Evaluate and store idempotent threshold alerts"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Evaluates real-time actual spending vs budget allocations using authoritative transactions.
    Computes linear period-end projections and logs threshold alerts.
    """
    service = BudgetService(session)
    data = await service.get_budget_progress(
        budget_id=budget_id,
        workspace_id=context.workspace_id,
        as_of_date=as_of_date,
        evaluate_alerts=evaluate_alerts,
    )
    return ApiResponse(data=BudgetProgressResponse.model_validate(data))


@router.get(
    "/{budget_id}/revisions",
    response_model=ApiResponse[List[BudgetRevisionResponse]],
    summary="List Budget Audit Revisions",
)
async def list_budget_revisions(
    budget_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves full audit revision history showing every parameter modification."""
    service = BudgetService(session)
    revisions = await service.list_revisions(budget_id, context.workspace_id)
    items = []
    total_revs = len(revisions)
    for idx, r in enumerate(revisions):
        rev_num = total_revs - idx
        items.append(
            BudgetRevisionResponse(
                id=r.id,
                budget_id=r.budget_id,
                revision_number=rev_num,
                change_type=r.revision_type,
                previous_state={"amount_paise": r.previous_amount_paise},
                new_state={"amount_paise": r.new_amount_paise},
                reason=r.change_reason,
                changed_by_id=r.changed_by_id,
                created_at=r.created_at,
            )
        )
    return ApiResponse(data=items)


@router.get(
    "/{budget_id}/alerts",
    response_model=ApiResponse[List[BudgetAlertResponse]],
    summary="List Triggered Budget Alerts",
)
async def list_budget_alerts(
    budget_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves all triggered threshold crossing alerts for the budget."""
    service = BudgetService(session)
    alerts = await service.list_alerts(budget_id, context.workspace_id)
    items = [
        BudgetAlertResponse(
            id=a.id,
            budget_id=a.budget_id,
            allocation_id=a.allocation_id,
            category_name=None,
            threshold_percentage=a.threshold_percentage,
            triggered_at_paise=a.actual_spent_paise,
            triggered_at_amount=Decimal(a.actual_spent_paise) / Decimal(100),
            utilization_percentage=float(a.utilization_percentage),
            message=a.message,
            created_at=a.created_at,
        )
        for a in alerts
    ]
    return ApiResponse(data=items)


@router.post(
    "/{budget_id}/rollover",
    response_model=ApiResponse[BudgetDetailResponse],
    summary="Roll Over Budget to Next Period",
)
async def rollover_budget(
    budget_id: uuid.UUID,
    payload: BudgetRolloverRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Clones the budget and its category allocations into the subsequent period.
    """
    service = BudgetService(session)
    new_budget = await service.rollover_budget(
        budget_id=budget_id,
        workspace_id=context.workspace_id,
        new_start_date=payload.new_start_date,
        new_end_date=payload.new_end_date,
        adjust_allocation_paise=payload.adjust_allocation_paise,
        created_by_id=context.user.id,
    )
    full_new = await service.get_budget(new_budget.id, context.workspace_id)
    return ApiResponse(data=_map_budget_detail(full_new))


# --- Category Allocation Management ---

@router.post(
    "/{budget_id}/allocations",
    response_model=ApiResponse[BudgetDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Category Allocation to Budget",
)
async def add_allocation(
    budget_id: uuid.UUID,
    payload: AllocationCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Adds a category ceiling to the budget and records an audit revision."""
    service = BudgetService(session)
    await service.add_allocation(
        budget_id=budget_id,
        workspace_id=context.workspace_id,
        category_id=payload.category_id,
        allocated_amount_paise=payload.allocated_amount_paise,
        warning_threshold_percentage=payload.warning_threshold_percentage or 80,
        notes=payload.notes,
        revision_reason=payload.revision_reason,
        changed_by_id=context.user.id,
    )
    budget = await service.get_budget(budget_id, context.workspace_id)
    return ApiResponse(data=_map_budget_detail(budget))


@router.patch(
    "/{budget_id}/allocations/{allocation_id}",
    response_model=ApiResponse[BudgetDetailResponse],
    summary="Update Category Allocation",
)
async def update_allocation(
    budget_id: uuid.UUID,
    allocation_id: uuid.UUID,
    payload: AllocationUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates a category allocation ceiling and records an audit revision."""
    service = BudgetService(session)
    await service.update_allocation(
        budget_id=budget_id,
        allocation_id=allocation_id,
        workspace_id=context.workspace_id,
        allocated_amount_paise=payload.allocated_amount_paise,
        warning_threshold_percentage=payload.warning_threshold_percentage,
        notes=payload.notes,
        revision_reason=payload.revision_reason,
        changed_by_id=context.user.id,
    )
    budget = await service.get_budget(budget_id, context.workspace_id)
    return ApiResponse(data=_map_budget_detail(budget))


@router.delete(
    "/{budget_id}/allocations/{allocation_id}",
    response_model=ApiResponse[BudgetDetailResponse],
    summary="Remove Category Allocation",
)
async def remove_allocation(
    budget_id: uuid.UUID,
    allocation_id: uuid.UUID,
    reason: Optional[str] = Query(None, description="Audit reason for removing category allocation"),
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUDGETS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Removes a category allocation from the budget and logs an audit revision."""
    service = BudgetService(session)
    await service.remove_allocation(
        budget_id=budget_id,
        allocation_id=allocation_id,
        workspace_id=context.workspace_id,
        revision_reason=reason,
        changed_by_id=context.user.id,
    )
    budget = await service.get_budget(budget_id, context.workspace_id)
    return ApiResponse(data=_map_budget_detail(budget))
