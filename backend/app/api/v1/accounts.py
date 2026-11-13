"""
Arthsavora V1 Financial Accounts Endpoints
Manages bank, credit card, cash, and wallet accounts scoped to the active workspace.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_workspace_context, require_role
from app.core.permissions import WorkspaceContext
from app.infrastructure.database.models.workspace import WorkspaceRole
from app.infrastructure.database.session import get_db_session
from app.schemas.account import AccountCreateRequest, AccountResponse
from app.services.account_service import AccountService

router = APIRouter(tags=["Financial Accounts"])


@router.get(
    "/",
    response_model=List[AccountResponse],
    summary="List all financial accounts in current workspace",
)
async def list_accounts(
    account_type: Optional[str] = Query(None, description="Optional account type filter"),
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves all active financial accounts belonging to the resolved workspace."""
    accounts = await AccountService.list_accounts(session, context, account_type)
    return [AccountResponse.model_validate(a) for a in accounts]


@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a financial account in current workspace",
)
async def create_account(
    data: AccountCreateRequest,
    context: WorkspaceContext = Depends(
        require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])
    ),
    session: AsyncSession = Depends(get_db_session),
):
    """Provisions a new bank, cash, or credit account. Requires OWNER or ADMIN role."""
    account = await AccountService.create_account(session, context, data)
    return AccountResponse.model_validate(account)
