"""
Arthsavora Family Finance API Endpoints
REST endpoints for household dashboards, member management, exact-paise expense allocations,
pool contributions, privacy bridges, and settlement recommendations.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_current_workspace_context,
)
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db_session
from app.schemas.family_schema import (
    CreateAllocationRequest,
    FamilyAllocationResponse,
    FamilyContributionResponse,
    FamilyMemberResponse,
    FamilyOverviewResponse,
    FamilyProfileResponse,
    FamilySettlementSummaryResponse,
    InviteFamilyMemberRequest,
    RecordContributionRequest,
    SharedAccountResponse,
    ShareAccountRequest,
    UpdateContributionRequest,
    UpdateFamilyMemberRoleRequest,
    UpdateFamilyProfileRequest,
)
from app.schemas.workspace import CreateInvitationRequest, UpdateMemberRoleRequest
from app.services.family_service import FamilyService
from app.services.invitation_service import InvitationService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# -----------------------------------------------------------------------------
# Overview & Profile
# -----------------------------------------------------------------------------

@router.get(
    "/overview",
    response_model=FamilyOverviewResponse,
    summary="Get Family Dashboard Overview",
    description="Returns consolidated household financial snapshot including income, expenses, shared balances, and budget progress.",
)
async def get_family_overview(
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilyOverviewResponse:
    service = FamilyService(session)
    return await service.get_family_overview(context)


@router.get(
    "/profile",
    response_model=FamilyProfileResponse,
    summary="Get Family Profile",
    description="Retrieves the family workspace preferences, timezone, base currency, and default allocation rules.",
)
async def get_family_profile(
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilyProfileResponse:
    service = FamilyService(session)
    return await service.get_family_profile(context)


@router.put(
    "/profile",
    response_model=FamilyProfileResponse,
    summary="Update Family Profile",
    description="Updates family workspace settings (household name, currency, reminder days, allocation defaults).",
)
async def update_family_profile(
    data: UpdateFamilyProfileRequest,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilyProfileResponse:
    service = FamilyService(session)
    return await service.update_family_profile(context, data)


# -----------------------------------------------------------------------------
# Member Management
# -----------------------------------------------------------------------------

@router.get(
    "/members",
    response_model=List[FamilyMemberResponse],
    summary="List Family Members",
    description="Lists all active members in this family workspace.",
)
async def list_family_members(
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> List[FamilyMemberResponse]:
    service = FamilyService(session)
    return await service.list_members(context)


@router.post(
    "/members/invite",
    status_code=status.HTTP_201_CREATED,
    summary="Invite Family Member",
    description="Issues a secure invitation to an email address with specified household role.",
)
async def invite_family_member(
    data: InviteFamilyMemberRequest,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    req = CreateInvitationRequest(email=data.email, role=data.role)
    invitation, raw_token = await InvitationService.create_invitation(
        session=session,
        context=context,
        data=req,
    )
    return {
        "invitation_id": str(invitation.id),
        "email": invitation.email,
        "role": invitation.role,
        "status": invitation.status,
        "expires_at": invitation.expires_at.isoformat(),
        "invitation_token": raw_token,
    }


@router.patch(
    "/members/{member_id}/role",
    response_model=Dict[str, Any],
    summary="Update Member Role",
    description="Updates a member's role (admin, member, restricted, viewer).",
)
async def update_family_member_role(
    member_id: UUID,
    data: UpdateFamilyMemberRoleRequest,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    req = UpdateMemberRoleRequest(role=data.role)
    return await WorkspaceService.update_member_role(
        session=session,
        context=context,
        membership_id=member_id,
        data=req,
    )


@router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Family Member",
    description="Revokes a member's access from the family workspace immediately.",
)
async def remove_family_member(
    member_id: UUID,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await WorkspaceService.remove_member(
        session=session,
        context=context,
        membership_id=member_id,
    )


# -----------------------------------------------------------------------------
# Expense Allocations
# -----------------------------------------------------------------------------

@router.get(
    "/allocations",
    summary="List Expense Allocations",
    description="Returns paginated list of shared expense allocations in this family workspace.",
)
async def list_allocations(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    service = FamilyService(session)
    allocations, total = await service.list_allocations(
        context=context,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": allocations,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/allocations",
    response_model=FamilyAllocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Expense Allocation",
    description="Allocates a shared household expense among family members with exact minor unit precision.",
)
async def create_expense_allocation(
    data: CreateAllocationRequest,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilyAllocationResponse:
    service = FamilyService(session)
    return await service.create_expense_allocation(context, data)


@router.get(
    "/allocations/{allocation_id}",
    response_model=FamilyAllocationResponse,
    summary="Get Allocation Detail",
    description="Retrieves a single allocation record with member shares.",
)
async def get_allocation_detail(
    allocation_id: UUID,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilyAllocationResponse:
    service = FamilyService(session)
    return await service._to_allocation_response(allocation_id, context.workspace.id)


# -----------------------------------------------------------------------------
# Member Contributions
# -----------------------------------------------------------------------------

@router.get(
    "/contributions",
    summary="List Member Contributions",
    description="Returns paginated list of expected and recorded member contributions.",
)
async def list_contributions(
    period: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    member_user_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    service = FamilyService(session)
    contribs, total = await service.list_contributions(
        context=context,
        period=period,
        member_user_id=member_user_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": contribs,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/contributions",
    response_model=FamilyContributionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Member Contribution",
    description="Records an expected or paid member contribution into the household fund.",
)
async def record_contribution(
    data: RecordContributionRequest,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilyContributionResponse:
    service = FamilyService(session)
    return await service.record_contribution(context, data)


@router.patch(
    "/contributions/{contribution_id}",
    response_model=FamilyContributionResponse,
    summary="Update Contribution",
    description="Updates paid amount, status, or notes on an existing contribution.",
)
async def update_contribution(
    contribution_id: UUID,
    data: UpdateContributionRequest,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilyContributionResponse:
    service = FamilyService(session)
    return await service.update_contribution(context, contribution_id, data)


# -----------------------------------------------------------------------------
# Settlements
# -----------------------------------------------------------------------------

@router.get(
    "/settlements",
    response_model=FamilySettlementSummaryResponse,
    summary="Get Household Settlement Summary",
    description="Calculates net standing for each member and produces peer settlement recommendations.",
)
async def get_settlement_summary(
    period: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> FamilySettlementSummaryResponse:
    service = FamilyService(session)
    return await service.get_settlement_summary(context, period)


# -----------------------------------------------------------------------------
# Shared Personal Accounts (Privacy Bridge)
# -----------------------------------------------------------------------------

@router.get(
    "/shared-accounts",
    response_model=List[SharedAccountResponse],
    summary="List Accounts Shared with Family",
    description="Lists personal accounts selectively shared with the household.",
)
async def list_shared_accounts(
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> List[SharedAccountResponse]:
    service = FamilyService(session)
    return await service.list_shared_accounts(context)


@router.post(
    "/shared-accounts",
    response_model=SharedAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Share Personal Account",
    description="Shares a member's personal account balance with the family workspace.",
)
async def share_personal_account(
    data: ShareAccountRequest,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> SharedAccountResponse:
    service = FamilyService(session)
    return await service.share_personal_account(
        context=context,
        account_id=data.account_id,
        share_scope=data.share_scope,
        notes=data.notes,
    )


@router.delete(
    "/shared-accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Account Sharing",
    description="Revokes a personal account's visibility from the family workspace.",
)
async def revoke_account_sharing(
    account_id: UUID,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    service = FamilyService(session)
    await service.revoke_account_share(context, account_id)


# -----------------------------------------------------------------------------
# Activity Timeline
# -----------------------------------------------------------------------------

@router.get(
    "/activity",
    summary="Get Family Activity Timeline",
    description="Returns chronological audit timeline of family workspace events.",
)
async def get_family_activity(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    service = FamilyService(session)
    activities, total = await service.list_activities(context, limit=limit, offset=offset)
    return {
        "items": activities,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
