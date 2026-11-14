"""
Arthsavora V1 Financial Accounts Endpoints
Manages bank, credit card, cash, loan, wallet, and investment accounts,
along with lifecycle transitions and point-in-time balance snapshot histories.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_workspace_context, require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.account import (
    AccountBalanceSnapshotCreateRequest,
    AccountBalanceSnapshotResponse,
    AccountCloseRequest,
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
    BalanceBreakdown,
)
from app.services.account_service import AccountService

router = APIRouter(tags=["Financial Accounts"])


# ---------------------------------------------------------------------------
# Account Collection (List & Create)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[AccountResponse],
    summary="List all financial accounts in current workspace",
)
@router.get(
    "/",
    response_model=List[AccountResponse],
    include_in_schema=False,
)
async def list_accounts(
    account_type: Optional[str] = Query(None, description="Optional account type filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, inactive, archived, closed)"),
    include_archived: bool = Query(False, description="Whether to include archived and closed accounts"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves financial accounts strictly scoped to the active workspace context."""
    return await AccountService.list_accounts(
        session=session,
        workspace_context=context,
        account_type=account_type,
        status=status_filter,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a financial account in current workspace",
)
@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_account(
    data: AccountCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Provisions a normalized financial account:
    - Validates account type compatibility for workspace tenancy model (Personal/Family/Business).
    - Validates currency using Money domain value object.
    - Prevents duplicate linked provider references within the workspace.
    - Quantizes opening balance and seeds initial balance snapshot.
    """
    return await AccountService.create_account(session, context, data)


# ---------------------------------------------------------------------------
# Individual Account (Detail & Update)
# ---------------------------------------------------------------------------


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get financial account by ID",
)
async def get_account(
    account_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves account details by ID scoped to workspace. Returns 404 on cross-workspace IDOR attempt."""
    return await AccountService.get_account(session, context, account_id)


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update financial account details",
)
async def update_account(
    account_id: uuid.UUID,
    data: AccountUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates mutable metadata, credit limits, or notes. Prohibits updating closed or archived accounts."""
    return await AccountService.update_account(session, context, account_id, data)


# ---------------------------------------------------------------------------
# Account Lifecycle Transitions
# ---------------------------------------------------------------------------


@router.post(
    "/{account_id}/archive",
    response_model=AccountResponse,
    summary="Archive a financial account",
)
async def archive_account(
    account_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Transitions active account into read-only ARCHIVED state while preserving historical reporting."""
    return await AccountService.archive_account(session, context, account_id)


@router.post(
    "/{account_id}/restore",
    response_model=AccountResponse,
    summary="Restore an archived financial account",
)
async def restore_account(
    account_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Restores an ARCHIVED account back to ACTIVE status."""
    return await AccountService.restore_account(session, context, account_id)


@router.post(
    "/{account_id}/close",
    response_model=AccountResponse,
    summary="Formally close a financial account",
)
async def close_account(
    account_id: uuid.UUID,
    data: AccountCloseRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Formally marks account as CLOSED. Validates closing_date >= opening_date."""
    return await AccountService.close_account(session, context, account_id, data)


# ---------------------------------------------------------------------------
# Balance Architecture & History Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{account_id}/balances",
    response_model=BalanceBreakdown,
    summary="Get structured balance breakdown",
)
async def get_account_balances(
    account_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns unambiguous balance values:
    - Book balance (derived from posted transactions and journals).
    - Available balance (reported or calculated).
    - Provider-reported balance (with effective timestamp).
    - Outstanding liability (credit cards / loans).
    - Pending transaction amount.
    - Opening balance.
    """
    return await AccountService.get_account_balances(session, context, account_id)


@router.get(
    "/{account_id}/balance-history",
    response_model=List[AccountBalanceSnapshotResponse],
    summary="Get historical balance snapshots",
)
async def list_balance_history(
    account_id: uuid.UUID,
    balance_type: Optional[str] = Query(None, description="Filter by balance type (book, available, provider_reported, liability, opening)"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves point-in-time balance snapshot history in reverse chronological order."""
    return await AccountService.list_balance_history(
        session=session,
        workspace_context=context,
        account_id=account_id,
        balance_type=balance_type,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{account_id}/balances/snapshot",
    response_model=AccountBalanceSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a point-in-time balance snapshot",
)
async def record_balance_snapshot(
    account_id: uuid.UUID,
    data: AccountBalanceSnapshotCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ACCOUNTS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Records an immutable balance snapshot (provider feed, manual count, statement reconcile)."""
    return await AccountService.record_balance_snapshot(session, context, account_id, data)
