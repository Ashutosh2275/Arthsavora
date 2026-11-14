"""
Arthsavora V1 Operational Transactions & Transfers Endpoints
Intake, paginated queries, lifecycle mutations, immutability enforcement,
paired transfers, cumulative refunds, and auditable history for operational financial movements.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_workspace_context, require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    TransactionCancelRequest,
    TransactionCreateRequest,
    TransactionHistoryEntry,
    TransactionPostRequest,
    TransactionRefundRequest,
    TransactionResponse,
    TransactionReverseRequest,
    TransactionUpdateRequest,
    TransferCreateRequest,
    TransferResponse,
)
from app.services.transaction_service import TransactionService

router = APIRouter(tags=["Operational Transactions"])
transfers_router = APIRouter(tags=["Transfers"])


# ---------------------------------------------------------------------------
# Transaction Collection (List & Intake)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List paginated transactions for current workspace",
)
@router.get(
    "/",
    response_model=PaginatedResponse[TransactionResponse],
    include_in_schema=False,
)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    account_id: Optional[uuid.UUID] = Query(None, description="Filter by account UUID"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category UUID"),
    status: Optional[str] = Query(None, description="Filter by status (pending, posted, failed, cancelled, reversed)"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    direction: Optional[str] = Query(None, description="Filter by direction (inflow, outflow, neutral)"),
    start_date: Optional[date] = Query(None, description="Start date filter (inclusive)"),
    end_date: Optional[date] = Query(None, description="End date filter (inclusive)"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount filter"),
    max_amount: Optional[Decimal] = Query(None, description="Maximum amount filter"),
    search: Optional[str] = Query(None, description="Text search across description and merchant name"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves paginated transactions strictly scoped to the caller's workspace context."""
    offset = (page - 1) * page_size
    items, total = await TransactionService.list_transactions(
        session=session,
        workspace_context=context,
        limit=page_size,
        offset=offset,
        account_id=account_id,
        category_id=category_id,
        status=status,
        transaction_type=transaction_type,
        direction=direction,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[TransactionService.format_transaction_response(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record or intake a financial transaction",
)
@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_transaction(
    data: TransactionCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.CREATE_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Intakes an operational transaction with Money validation and external ID deduplication.
    Requires active workspace membership with creation privileges.
    """
    tx, is_new = await TransactionService.intake_transaction(session, context, data)
    return TransactionService.format_transaction_response(tx)


# ---------------------------------------------------------------------------
# Individual Transaction Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get single transaction by ID",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves a single operational transaction. Returns 404 anti-IDOR if cross-workspace."""
    tx = await TransactionService.get_transaction(session, context, transaction_id)
    return TransactionService.format_transaction_response(tx)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update editable transaction metadata",
)
async def update_transaction(
    transaction_id: uuid.UUID,
    data: TransactionUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.UPDATE_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Updates non-financial metadata (description, merchant, category, tags).
    Strictly prohibits modifying financial facts on posted transactions.
    """
    tx = await TransactionService.update_transaction(session, context, transaction_id, data)
    return TransactionService.format_transaction_response(tx)


# ---------------------------------------------------------------------------
# Lifecycle State Machine Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{transaction_id}/post",
    response_model=TransactionResponse,
    summary="Post a pending transaction to clear it",
)
async def post_transaction(
    transaction_id: uuid.UUID,
    data: Optional[TransactionPostRequest] = None,
    context: WorkspaceContext = Depends(require_permission(Permission.CREATE_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Transitions a pending transaction to posted and impacts account balances."""
    tx = await TransactionService.post_transaction(session, context, transaction_id, data)
    return TransactionService.format_transaction_response(tx)


@router.post(
    "/{transaction_id}/cancel",
    response_model=TransactionResponse,
    summary="Cancel an unposted pending transaction",
)
async def cancel_transaction(
    transaction_id: uuid.UUID,
    data: Optional[TransactionCancelRequest] = None,
    context: WorkspaceContext = Depends(require_permission(Permission.CREATE_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Cancels a pending transaction and restores available balance."""
    tx = await TransactionService.cancel_transaction(session, context, transaction_id, data)
    return TransactionService.format_transaction_response(tx)


@router.post(
    "/{transaction_id}/reverse",
    response_model=TransactionResponse,
    summary="Issue a formal reversal for a posted transaction",
)
async def reverse_transaction(
    transaction_id: uuid.UUID,
    data: TransactionReverseRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.CREATE_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Formally reverses a posted transaction by inverting account balances and
    generating an auditable compensating reversal record.
    """
    rev_tx = await TransactionService.reverse_transaction(session, context, transaction_id, data)
    return TransactionService.format_transaction_response(rev_tx)


@router.post(
    "/{transaction_id}/refunds",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a partial or full refund for a posted transaction",
)
async def refund_transaction(
    transaction_id: uuid.UUID,
    data: TransactionRefundRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.CREATE_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Issues a refund for an outflow transaction, enforcing that cumulative refunds
    cannot exceed the original amount.
    """
    refund_tx = await TransactionService.refund_transaction(session, context, transaction_id, data)
    return TransactionService.format_transaction_response(refund_tx)


@router.get(
    "/{transaction_id}/history",
    response_model=List[TransactionHistoryEntry],
    summary="Get auditable change history for a transaction",
)
async def get_transaction_history(
    transaction_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves immutable audit history log for a transaction."""
    return await TransactionService.get_transaction_history(session, context, transaction_id)


# ---------------------------------------------------------------------------
# Transfer Endpoints
# ---------------------------------------------------------------------------


@transfers_router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an internal transfer between accounts",
)
@transfers_router.post(
    "/",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_transfer(
    data: TransferCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.CREATE_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Executes an internal transfer creating paired source (outflow) and destination (inflow) legs.
    Handles credit card debt reduction without double-counting expenses.
    """
    return await TransactionService.create_transfer(session, context, data)


@transfers_router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    summary="Get paired transfer details by transfer ID",
)
async def get_transfer(
    transfer_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves paired transfer legs by transfer UUID."""
    return await TransactionService.get_transfer(session, context, transfer_id)
