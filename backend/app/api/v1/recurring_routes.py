"""
Arthsavora Recurring Transactions, Subscriptions & Cash-Flow Commitments API Endpoints
Authenticated, workspace-scoped RESTful routes for recurring definitions, occurrences,
subscriptions, pattern detection suggestions, and forward-looking cash-flow commitments.
"""

from datetime import date
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.common import ApiResponse
from app.schemas.recurring_schema import (
    CashFlowCommitmentsResponse,
    OccurrenceConfirmRequest,
    OccurrenceMatchRequest,
    OccurrenceResponse,
    OccurrenceSkipRequest,
    RecurringDefinitionCreateRequest,
    RecurringDefinitionResponse,
    RecurringDefinitionUpdateRequest,
    RecurringDetectRequest,
    RecurringSuggestionResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    SuggestionConfirmRequest,
    SuggestionDismissRequest,
)
from app.services.recurring.commitment_service import CommitmentService
from app.services.recurring.detection_service import DetectionService
from app.services.recurring.matching_service import MatchingService
from app.services.recurring.recurring_service import RecurringService
from app.services.recurring.subscription_service import SubscriptionService

router = APIRouter(tags=["Recurring Transactions, Subscriptions & Commitments"])


# -------------------------------------------------------------------------
# Recurring Definitions
# -------------------------------------------------------------------------

@router.get(
    "",
    response_model=ApiResponse[List[RecurringDefinitionResponse]],
    summary="List Recurring Definitions",
)
async def list_recurring_definitions(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, paused, cancelled)"),
    direction: Optional[str] = Query(None, description="Filter by direction (inflow, outflow)"),
    frequency: Optional[str] = Query(None, description="Filter by frequency"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Lists recurring definitions scoped to current workspace."""
    service = RecurringService(session)
    items = await service.list_definitions(
        workspace_id=context.workspace_id,
        status=status_filter,
        direction=direction,
        frequency=frequency,
        skip=skip,
        limit=limit,
    )
    return ApiResponse(data=items)


@router.post(
    "",
    response_model=ApiResponse[RecurringDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Recurring Definition",
)
async def create_recurring_definition(
    payload: RecurringDefinitionCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Creates a new recurring definition and automatically generates initial occurrences."""
    service = RecurringService(session)
    created = await service.create_definition(
        workspace_id=context.workspace_id,
        payload=payload,
        created_by_id=context.current_user.id if context.current_user else None,
    )
    return ApiResponse(data=created)


@router.get(
    "/{recurring_id}",
    response_model=ApiResponse[RecurringDefinitionResponse],
    summary="Get Recurring Definition Details",
)
async def get_recurring_definition(
    recurring_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves single recurring definition by ID."""
    service = RecurringService(session)
    item = await service.get_definition(
        definition_id=recurring_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=item)


@router.patch(
    "/{recurring_id}",
    response_model=ApiResponse[RecurringDefinitionResponse],
    summary="Update Recurring Definition",
)
async def update_recurring_definition(
    recurring_id: uuid.UUID,
    payload: RecurringDefinitionUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates parameters of a recurring definition."""
    service = RecurringService(session)
    updated = await service.update_definition(
        definition_id=recurring_id,
        workspace_id=context.workspace_id,
        payload=payload,
    )
    return ApiResponse(data=updated)


@router.post(
    "/{recurring_id}/pause",
    response_model=ApiResponse[RecurringDefinitionResponse],
    summary="Pause Recurring Schedule",
)
async def pause_recurring_definition(
    recurring_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Pauses an active recurring schedule."""
    service = RecurringService(session)
    updated = await service.pause_definition(
        definition_id=recurring_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=updated)


@router.post(
    "/{recurring_id}/resume",
    response_model=ApiResponse[RecurringDefinitionResponse],
    summary="Resume Recurring Schedule",
)
async def resume_recurring_definition(
    recurring_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Resumes a paused recurring schedule and regenerates future occurrences."""
    service = RecurringService(session)
    updated = await service.resume_definition(
        definition_id=recurring_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=updated)


@router.post(
    "/{recurring_id}/cancel",
    response_model=ApiResponse[RecurringDefinitionResponse],
    summary="Cancel Recurring Schedule",
)
async def cancel_recurring_definition(
    recurring_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Cancels a recurring schedule."""
    service = RecurringService(session)
    updated = await service.cancel_definition(
        definition_id=recurring_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=updated)


# -------------------------------------------------------------------------
# Occurrences
# -------------------------------------------------------------------------

@router.get(
    "/occurrences/list",
    response_model=ApiResponse[List[OccurrenceResponse]],
    summary="List Scheduled Occurrences",
)
async def list_occurrences(
    recurring_id: Optional[uuid.UUID] = Query(None, description="Filter by recurring definition ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (scheduled, due, overdue, matched, confirmed, skipped)"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Lists scheduled occurrences across the workspace or for a specific definition."""
    service = RecurringService(session)
    items = await service.list_occurrences(
        workspace_id=context.workspace_id,
        definition_id=recurring_id,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return ApiResponse(data=items)


@router.post(
    "/occurrences/{occurrence_id}/skip",
    response_model=ApiResponse[OccurrenceResponse],
    summary="Skip Scheduled Occurrence",
)
async def skip_occurrence(
    occurrence_id: uuid.UUID,
    payload: OccurrenceSkipRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Marks an occurrence as skipped by the user without modifying historical transactions."""
    service = RecurringService(session)
    updated = await service.skip_occurrence(
        occurrence_id=occurrence_id,
        workspace_id=context.workspace_id,
        reason=payload.reason,
    )
    return ApiResponse(data=updated)


@router.post(
    "/occurrences/{occurrence_id}/confirm",
    response_model=ApiResponse[OccurrenceResponse],
    summary="Confirm Occurrence",
)
async def confirm_occurrence(
    occurrence_id: uuid.UUID,
    payload: OccurrenceConfirmRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Manually confirms that a scheduled occurrence has taken place."""
    service = RecurringService(session)
    updated = await service.confirm_occurrence(
        occurrence_id=occurrence_id,
        workspace_id=context.workspace_id,
        notes=payload.notes,
    )
    return ApiResponse(data=updated)


@router.get(
    "/occurrences/{occurrence_id}/candidates",
    response_model=ApiResponse[List[Dict[str, Any]]],
    summary="Find Candidate Matches for Occurrence",
)
async def find_occurrence_candidates(
    occurrence_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Finds candidate posted transactions within +/- 10 days and calculates matching heuristics."""
    service = MatchingService(session)
    candidates = await service.find_matches_for_occurrence(
        occurrence_id=occurrence_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=candidates)


@router.post(
    "/occurrences/{occurrence_id}/match",
    response_model=ApiResponse[OccurrenceResponse],
    summary="Match Occurrence to Actual Transaction",
)
async def match_occurrence(
    occurrence_id: uuid.UUID,
    payload: OccurrenceMatchRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Reconciles an occurrence with an actual posted transaction."""
    service = MatchingService(session)
    updated = await service.match_occurrence_to_transaction(
        occurrence_id=occurrence_id,
        workspace_id=context.workspace_id,
        transaction_id=payload.transaction_id,
        notes=payload.notes,
    )
    return ApiResponse(data=updated)


@router.post(
    "/occurrences/{occurrence_id}/unmatch",
    response_model=ApiResponse[OccurrenceResponse],
    summary="Unmatch Occurrence from Transaction",
)
async def unmatch_occurrence(
    occurrence_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Removes reconciliation association and restores occurrence status."""
    service = MatchingService(session)
    updated = await service.unmatch_occurrence(
        occurrence_id=occurrence_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=updated)


# -------------------------------------------------------------------------
# Subscriptions
# -------------------------------------------------------------------------

@router.get(
    "/subscriptions/list",
    response_model=ApiResponse[List[SubscriptionResponse]],
    summary="List Subscriptions",
)
async def list_subscriptions(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, trial, paused, cancelled)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_SUBSCRIPTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Lists subscriptions with normalized monthly and annual costs."""
    service = SubscriptionService(session)
    items = await service.list_subscriptions(
        workspace_id=context.workspace_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return ApiResponse(data=items)


@router.post(
    "/subscriptions/create",
    response_model=ApiResponse[SubscriptionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Subscription",
)
async def create_subscription(
    payload: SubscriptionCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_SUBSCRIPTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Creates a new subscription with optional backing recurring definition."""
    service = SubscriptionService(session)
    created = await service.create_subscription(
        workspace_id=context.workspace_id,
        payload=payload,
        created_by_id=context.current_user.id if context.current_user else None,
    )
    return ApiResponse(data=created)


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=ApiResponse[SubscriptionResponse],
    summary="Get Subscription Details",
)
async def get_subscription(
    subscription_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_SUBSCRIPTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Fetch single subscription detail."""
    service = SubscriptionService(session)
    item = await service.get_subscription(
        subscription_id=subscription_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=item)


@router.patch(
    "/subscriptions/{subscription_id}",
    response_model=ApiResponse[SubscriptionResponse],
    summary="Update Subscription",
)
async def update_subscription(
    subscription_id: uuid.UUID,
    payload: SubscriptionUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_SUBSCRIPTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates subscription parameters."""
    service = SubscriptionService(session)
    updated = await service.update_subscription(
        subscription_id=subscription_id,
        workspace_id=context.workspace_id,
        payload=payload,
    )
    return ApiResponse(data=updated)


@router.post(
    "/subscriptions/{subscription_id}/cancel",
    response_model=ApiResponse[SubscriptionResponse],
    summary="Cancel Subscription",
)
async def cancel_subscription(
    subscription_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_SUBSCRIPTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Cancels a subscription and stops future occurrences."""
    service = SubscriptionService(session)
    updated = await service.cancel_subscription(
        subscription_id=subscription_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=updated)


# -------------------------------------------------------------------------
# Recurring Pattern Detection & Suggestions
# -------------------------------------------------------------------------

@router.post(
    "/detect",
    response_model=ApiResponse[List[RecurringSuggestionResponse]],
    summary="Detect Recurring Patterns from History",
)
async def detect_recurring_patterns(
    payload: RecurringDetectRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Scans historical posted transactions and returns explainable recurring pattern suggestions."""
    service = DetectionService(session)
    suggestions = await service.run_detection(
        workspace_id=context.workspace_id,
        lookback_days=payload.lookback_days,
        as_of_date=payload.as_of_date,
    )
    return ApiResponse(data=suggestions)


@router.get(
    "/suggestions/list",
    response_model=ApiResponse[List[RecurringSuggestionResponse]],
    summary="List Recurring Suggestions",
)
async def list_suggestions(
    status_filter: Optional[str] = Query("pending", alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Lists inferred recurring suggestions awaiting user review."""
    service = DetectionService(session)
    items = await service.list_suggestions(
        workspace_id=context.workspace_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return ApiResponse(data=items)


@router.post(
    "/suggestions/{suggestion_id}/confirm",
    response_model=ApiResponse[RecurringSuggestionResponse],
    summary="Confirm Inferred Suggestion",
)
async def confirm_suggestion(
    suggestion_id: uuid.UUID,
    payload: SuggestionConfirmRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Confirms a suggestion, creating an authoritative recurring definition or subscription."""
    service = DetectionService(session)
    updated = await service.confirm_suggestion(
        suggestion_id=suggestion_id,
        workspace_id=context.workspace_id,
        payload=payload,
        confirmed_by_id=context.current_user.id if context.current_user else None,
    )
    return ApiResponse(data=updated)


@router.post(
    "/suggestions/{suggestion_id}/dismiss",
    response_model=ApiResponse[RecurringSuggestionResponse],
    summary="Dismiss Inferred Suggestion",
)
async def dismiss_suggestion(
    suggestion_id: uuid.UUID,
    payload: SuggestionDismissRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """Dismisses an inferred suggestion so it will not be resurfaced."""
    service = DetectionService(session)
    updated = await service.dismiss_suggestion(
        suggestion_id=suggestion_id,
        workspace_id=context.workspace_id,
        payload=payload,
    )
    return ApiResponse(data=updated)


# -------------------------------------------------------------------------
# Cash-Flow Commitments & Recurring Analytics
# -------------------------------------------------------------------------

@router.get(
    "/commitments/overview",
    response_model=ApiResponse[CashFlowCommitmentsResponse],
    summary="Expected Cash-Flow Commitments Overview",
)
async def get_commitments_overview(
    window_days: int = Query(30, ge=7, le=365, description="Commitment time window in days (7, 30, 90, 365)"),
    start_date: Optional[date] = Query(None, description="Starting date for evaluation"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_RECURRING)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Computes upcoming expected inflows, outflows, normalized monthly/annual costs,
    and commitments breakdown by category and type.
    """
    service = CommitmentService(session)
    commitments = await service.get_commitments(
        workspace_id=context.workspace_id,
        window_days=window_days,
        start_date=start_date,
    )
    return ApiResponse(data=commitments)
