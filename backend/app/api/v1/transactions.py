"""
Arthsavora V1 Operational Transactions Endpoints
Intake and paginated queries for operational financial movements with exact decimal precision.
"""

from datetime import date
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_workspace_context, require_role
from app.core.permissions import WorkspaceContext
from app.infrastructure.database.models.workspace import WorkspaceRole
from app.infrastructure.database.session import get_db_session
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import TransactionCreateRequest, TransactionResponse
from app.services.transaction_service import TransactionService

router = APIRouter(tags=["Operational Transactions"])


@router.get(
    "/",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List paginated transactions for current workspace",
)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    account_id: Optional[uuid.UUID] = Query(None, description="Filter by account"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves paginated transactions with bounded limits strictly scoped to workspace."""
    offset = (page - 1) * page_size
    items, total = await TransactionService.list_transactions(
        session=session,
        workspace_context=context,
        limit=page_size,
        offset=offset,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Intake or record a financial transaction",
)
async def create_transaction(
    data: TransactionCreateRequest,
    context: WorkspaceContext = Depends(
        require_role([
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.MEMBER,
            WorkspaceRole.ACCOUNTANT,
        ])
    ),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Intakes an operational transaction with Money validation and external ID deduplication.
    Requires active workspace membership with posting privileges.
    """
    tx, is_new = await TransactionService.intake_transaction(session, context, data)
    return TransactionResponse.model_validate(tx)
