"""
Arthsavora Financial Goal API Endpoints
Authenticated, workspace-scoped RESTful routes for personal savings goals,
contributions, withdrawals, immutable activity ledgers, and progress pacing calculations.
"""

from datetime import date
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.goal_schema import (
    GoalActivityRequest,
    GoalActivityResponse,
    GoalCreateRequest,
    GoalProgressResponse,
    GoalResponse,
    GoalUpdateRequest,
)
from app.services.budget.goal_service import GoalService

router = APIRouter(tags=["Financial Savings Goals"])


def _map_goal_response(g) -> GoalResponse:
    return GoalResponse(
        id=g.id,
        workspace_id=g.workspace_id,
        name=g.name,
        description=g.description,
        goal_type=g.goal_type,
        currency=g.currency,
        target_amount_paise=g.target_amount_paise,
        target_amount=g.target_amount,
        current_amount_paise=g.current_amount_paise,
        current_amount=g.current_amount,
        start_date=g.start_date,
        target_date=g.target_date,
        status=g.status,
        priority=g.priority,
        color=g.color,
        icon=g.icon,
        created_by_id=g.created_by_id,
        metadata_payload=g.metadata_payload or {},
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


def _map_activity_response(a) -> GoalActivityResponse:
    return GoalActivityResponse(
        id=a.id,
        goal_id=a.goal_id,
        workspace_id=a.workspace_id,
        activity_type=a.activity_type,
        amount_paise=a.amount_paise,
        amount=a.amount,
        currency=a.currency,
        resulting_balance_paise=a.resulting_balance_paise,
        transaction_id=a.transaction_id,
        notes=a.notes,
        performed_by_id=a.performed_by_id,
        created_at=a.created_at,
    )


@router.get(
    "",
    response_model=ApiResponse[List[GoalResponse]],
    summary="List Financial Goals",
)
async def list_goals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, completed, paused, archived)"),
    goal_type: Optional[str] = Query(None, description="Filter by goal type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves all savings goals in the active workspace."""
    service = GoalService(session)
    goals, total = await service.list_goals(
        workspace_id=context.workspace_id,
        status=status_filter,
        goal_type=goal_type,
        limit=limit,
        offset=offset,
    )
    items = [_map_goal_response(g) for g in goals]
    return ApiResponse(data=items)


@router.post(
    "",
    response_model=ApiResponse[GoalResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Financial Goal",
)
async def create_goal(
    payload: GoalCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Creates a new target-based savings goal."""
    service = GoalService(session)
    goal = await service.create_goal(
        workspace_id=context.workspace_id,
        name=payload.name,
        target_amount_paise=payload.target_amount_paise,
        goal_type=payload.goal_type,
        currency=payload.currency,
        start_date=payload.start_date,
        target_date=payload.target_date,
        priority=payload.priority,
        color=payload.color,
        icon=payload.icon,
        description=payload.description,
        created_by_id=context.user.id,
        metadata_payload=payload.metadata_payload,
    )
    return ApiResponse(data=_map_goal_response(goal))


@router.get(
    "/{goal_id}",
    response_model=ApiResponse[GoalResponse],
    summary="Get Financial Goal Details",
)
async def get_goal(
    goal_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves specific goal details verified within workspace boundary."""
    service = GoalService(session)
    goal = await service.get_goal(goal_id, context.workspace_id)
    return ApiResponse(data=_map_goal_response(goal))


@router.patch(
    "/{goal_id}",
    response_model=ApiResponse[GoalResponse],
    summary="Update Financial Goal",
)
async def update_goal(
    goal_id: uuid.UUID,
    payload: GoalUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates savings goal targets, priority, dates, or status."""
    service = GoalService(session)
    goal = await service.update_goal(
        goal_id=goal_id,
        workspace_id=context.workspace_id,
        name=payload.name,
        target_amount_paise=payload.target_amount_paise,
        target_date=payload.target_date,
        status=payload.status,
        priority=payload.priority,
        color=payload.color,
        icon=payload.icon,
        description=payload.description,
        metadata_payload=payload.metadata_payload,
    )
    return ApiResponse(data=_map_goal_response(goal))


@router.delete(
    "/{goal_id}",
    response_model=ApiResponse[dict],
    summary="Archive/Delete Financial Goal",
)
async def delete_goal(
    goal_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Soft-deletes and archives a financial goal."""
    service = GoalService(session)
    await service.delete_goal(goal_id, context.workspace_id)
    return ApiResponse(data={"message": f"Financial goal {goal_id} archived successfully."})


@router.post(
    "/{goal_id}/contributions",
    response_model=ApiResponse[GoalActivityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record Savings Contribution",
)
async def record_contribution(
    goal_id: uuid.UUID,
    payload: GoalActivityRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Records a capital allocation contribution into the savings goal.
    Updates the accumulated balance and appends to the immutable activity ledger.
    """
    service = GoalService(session)
    activity = await service.record_contribution(
        goal_id=goal_id,
        workspace_id=context.workspace_id,
        amount_paise=payload.amount_paise,
        transaction_id=payload.transaction_id,
        notes=payload.notes,
        performed_by_id=context.user.id,
    )
    return ApiResponse(data=_map_activity_response(activity))


@router.post(
    "/{goal_id}/withdrawals",
    response_model=ApiResponse[GoalActivityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record Goal Withdrawal",
)
async def record_withdrawal(
    goal_id: uuid.UUID,
    payload: GoalActivityRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Records a withdrawal from the savings goal back to available liquidity.
    Enforces non-negative balance protection and appends to the activity ledger.
    """
    service = GoalService(session)
    activity = await service.record_withdrawal(
        goal_id=goal_id,
        workspace_id=context.workspace_id,
        amount_paise=payload.amount_paise,
        notes=payload.notes,
        performed_by_id=context.user.id,
    )
    return ApiResponse(data=_map_activity_response(activity))


@router.get(
    "/{goal_id}/progress",
    response_model=ApiResponse[GoalProgressResponse],
    summary="Get Goal Progress & Pacing Metrics",
)
async def get_goal_progress(
    goal_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None, description="Evaluation date (defaults to today)"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Evaluates completion percentage, remaining amount, and required monthly contribution rate."""
    service = GoalService(session)
    data = await service.get_goal_progress(
        goal_id=goal_id,
        workspace_id=context.workspace_id,
        as_of_date=as_of_date,
    )
    return ApiResponse(data=GoalProgressResponse.model_validate(data))


@router.get(
    "/{goal_id}/activity",
    response_model=ApiResponse[List[GoalActivityResponse]],
    summary="List Goal Activity Ledger Entries",
)
async def list_goal_activities(
    goal_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_GOALS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves paginated audit ledger of all contributions and withdrawals for the goal."""
    service = GoalService(session)
    activities, total = await service.list_activities(
        goal_id=goal_id,
        workspace_id=context.workspace_id,
        limit=limit,
        offset=offset,
    )
    items = [_map_activity_response(a) for a in activities]
    return ApiResponse(data=items)
