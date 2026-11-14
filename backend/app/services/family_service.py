"""
Arthsavora Family Finance Application Service
Coordinates shared household budgets, member roles, exact-paise expense allocations,
pool contributions, privacy boundaries, and informational settlements.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext
from app.domain.family import (
    AccountShareScope,
    AllocationMethod,
    AllocationStatus,
    ContributionStatus,
    ContributionType,
    FamilyActivityType,
    FamilyRole,
    SettlementStatus,
    calculate_custom_allocation,
    calculate_equal_allocation,
    calculate_fixed_allocation,
    calculate_percentage_allocation,
    compute_settlement_recommendations,
)
from app.domain.notification import (
    NotificationCategory,
    NotificationEventType,
    NotificationPayloadVO,
    NotificationSeverity,
)
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.budget import Budget
from app.infrastructure.database.models.family import (
    FamilyAccountShare,
    FamilyActivity,
    FamilyExpenseAllocation,
    FamilyExpenseAllocationItem,
    FamilyMemberContribution,
    FamilyProfile,
)
from app.infrastructure.database.models.goal import FinancialGoal
from app.infrastructure.database.models.recurring import RecurringDefinition
from app.infrastructure.database.models.transaction import Transaction
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import WorkspaceMember
from app.repositories.family_repository import FamilyRepository
from app.schemas.family_schema import (
    AllocationItemResponse,
    CreateAllocationRequest,
    FamilyAllocationResponse,
    FamilyContributionResponse,
    FamilyMemberResponse,
    FamilyOverviewResponse,
    FamilyProfileResponse,
    FamilySettlementSummaryResponse,
    MemberSettlementResponse,
    RecordContributionRequest,
    SettlementRecommendationResponse,
    SharedAccountResponse,
    UpdateContributionRequest,
    UpdateFamilyProfileRequest,
    paise_to_decimal,
)
from app.services.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)


class FamilyService:
    """Application service orchestrating collaborative family finance workflows."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FamilyRepository(session)

    # -------------------------------------------------------------------------
    # Profile & Preferences
    # -------------------------------------------------------------------------

    async def get_family_profile(self, context: WorkspaceContext) -> FamilyProfileResponse:
        """Retrieves or provisions the family workspace profile."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        profile = await self.repo.get_or_create_profile(
            workspace_id=context.workspace.id,
            default_name=context.workspace.name,
            currency=context.workspace.default_currency,
            timezone_str=context.workspace.timezone,
        )
        return FamilyProfileResponse.model_validate(profile)

    async def update_family_profile(
        self,
        context: WorkspaceContext,
        data: UpdateFamilyProfileRequest,
    ) -> FamilyProfileResponse:
        """Updates family profile settings (requires admin or owner authority)."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        if not context.can(Permission.MANAGE_FAMILY_SETTINGS):
            raise InsufficientPermissionsException(
                message="Only household owners or administrators can update family preferences."
            )

        update_dict = data.model_dump(exclude_unset=True)
        profile = await self.repo.update_profile(context.workspace.id, update_dict)
        if not profile:
            raise NotFoundException(message="Family profile not found.")

        # Log to timeline
        await self.repo.record_activity(
            FamilyActivity(
                workspace_id=context.workspace.id,
                actor_user_id=context.current_user.id,
                activity_type=FamilyActivityType.PRIVACY_UPDATED.value,
                resource_type="profile",
                resource_id=str(profile.id),
                title="Household Preferences Updated",
                description=f"Family profile updated by {context.current_user.full_name}.",
                metadata_payload=update_dict,
            )
        )
        await self.session.commit()
        return FamilyProfileResponse.model_validate(profile)

    # -------------------------------------------------------------------------
    # Member Directory & Management
    # -------------------------------------------------------------------------

    async def list_members(self, context: WorkspaceContext) -> List[FamilyMemberResponse]:
        """Lists active family members with user information."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        members_with_users = await self.repo.list_family_members(context.workspace.id)
        return [
            FamilyMemberResponse(
                id=m.id,
                workspace_id=m.workspace_id,
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=m.role,
                status=m.status,
                joined_at=m.joined_at,
            )
            for m, u in members_with_users
        ]

    # -------------------------------------------------------------------------
    # Expense Allocations
    # -------------------------------------------------------------------------

    async def create_expense_allocation(
        self,
        context: WorkspaceContext,
        data: CreateAllocationRequest,
    ) -> FamilyAllocationResponse:
        """
        Creates an exact-paise allocation dividing a shared household transaction among members.
        Revises any prior active allocation for this transaction idempotently.
        """
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        if not context.can(Permission.MANAGE_FAMILY_ALLOCATIONS):
            raise InsufficientPermissionsException(message="Permission required to allocate household expenses.")

        # 1. Fetch and validate target transaction
        tx_stmt = select(Transaction).where(
            Transaction.id == data.transaction_id,
            Transaction.workspace_id == context.workspace.id,
        )
        tx_res = await self.session.execute(tx_stmt)
        tx = tx_res.scalar_one_or_none()
        if not tx:
            raise NotFoundException(message="Transaction not found in this family workspace.")

        if tx.direction != "outflow":
            raise ValidationException(message="Only outflow expense transactions can be allocated.")

        total_amount_paise = tx.amount_paise
        if total_amount_paise <= 0:
            total_amount_paise = int(tx.amount * Decimal(100))

        method_enum = AllocationMethod(data.allocation_method)
        payer_id = data.payer_user_id or tx.created_by_id or context.current_user.id

        # 2. Compute Allocation Items using pure domain algorithms
        if method_enum == AllocationMethod.EQUAL:
            member_ids = data.member_user_ids
            if not member_ids:
                # Default to all active family members
                all_members = await self.repo.list_family_members(context.workspace.id)
                member_ids = [u.id for _, u in all_members]

            items_vo = calculate_equal_allocation(
                total_amount_paise=total_amount_paise,
                member_user_ids=member_ids,
                payer_user_id=payer_id,
            )

        elif method_enum == AllocationMethod.PERCENTAGE:
            if not data.member_percentages:
                raise ValidationException(message="member_percentages dict required for percentage allocation.")
            pct_dict = {UUID(k): Decimal(str(v)) for k, v in data.member_percentages.items()}
            items_vo = calculate_percentage_allocation(
                total_amount_paise=total_amount_paise,
                member_percentages=pct_dict,
                payer_user_id=payer_id,
            )

        elif method_enum in (AllocationMethod.FIXED, AllocationMethod.CUSTOM):
            if not data.member_shares_paise:
                raise ValidationException(message="member_shares_paise dict required for fixed/custom allocation.")
            shares_dict = {UUID(k): int(v) for k, v in data.member_shares_paise.items()}
            items_vo = calculate_fixed_allocation(
                total_amount_paise=total_amount_paise,
                member_shares_paise=shares_dict,
                payer_user_id=payer_id,
            )
        else:
            raise ValidationException(message=f"Unsupported allocation method: {data.allocation_method}")

        # 3. Handle versioning of prior allocation for this transaction
        prior_alloc = await self.repo.get_allocation_by_transaction_id(tx.id, context.workspace.id)
        version = 1
        if prior_alloc:
            prior_alloc.status = AllocationStatus.REVISED.value
            version = prior_alloc.version + 1

        # 4. Save new Allocation Entity
        allocation = FamilyExpenseAllocation(
            workspace_id=context.workspace.id,
            transaction_id=tx.id,
            allocation_method=method_enum.value,
            total_amount_paise=total_amount_paise,
            currency=tx.currency,
            status=AllocationStatus.ACTIVE.value,
            version=version,
            notes=data.notes,
            created_by_id=context.current_user.id,
        )

        for item_vo in items_vo:
            alloc_item = FamilyExpenseAllocationItem(
                member_user_id=item_vo.member_user_id,
                assigned_share_paise=item_vo.assigned_share_paise,
                percentage=item_vo.percentage,
                is_paid_by=item_vo.is_paid_by,
                settlement_status=item_vo.settlement_status.value,
                notes=item_vo.notes,
            )
            allocation.items.append(alloc_item)

        await self.repo.create_allocation(allocation)

        # 5. Record activity timeline
        await self.repo.record_activity(
            FamilyActivity(
                workspace_id=context.workspace.id,
                actor_user_id=context.current_user.id,
                activity_type=FamilyActivityType.EXPENSE_ALLOCATED.value,
                resource_type="allocation",
                resource_id=str(allocation.id),
                title=f"Expense Allocated ({method_enum.value.capitalize()})",
                description=f"Transaction '{tx.description}' of ₹{paise_to_decimal(total_amount_paise)} allocated among {len(items_vo)} members.",
                metadata_payload={
                    "transaction_id": str(tx.id),
                    "total_amount_paise": total_amount_paise,
                    "method": method_enum.value,
                },
            )
        )

        # 6. Dispatch Prompt 20 Notification to allocated members
        try:
            notif_service = NotificationService(self.session)
            for item in items_vo:
                if item.member_user_id != context.current_user.id:
                    share_dec = paise_to_decimal(item.assigned_share_paise)
                    await notif_service.dispatch_notification(
                        NotificationPayloadVO(
                            recipient_user_id=item.member_user_id,
                            category=NotificationCategory.TRANSACTION,
                            event_type=NotificationEventType.TRANSACTION_CONFIRMED,
                            title="New Shared Expense Allocated",
                            message=f"You were allocated ₹{share_dec} for '{tx.description}' in your household workspace.",
                            severity=NotificationSeverity.INFO,
                            workspace_id=context.workspace.id,
                            action_url="/family?tab=allocations",
                            metadata={
                                "allocation_id": str(allocation.id),
                                "transaction_id": str(tx.id),
                                "share_paise": item.assigned_share_paise,
                            },
                        )
                    )
        except Exception as e:
            logger.warning(f"Could not dispatch allocation notification: {e}")

        await self.session.commit()
        return await self._to_allocation_response(allocation.id, context.workspace.id)

    async def list_allocations(
        self,
        context: WorkspaceContext,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FamilyAllocationResponse], int]:
        """Lists expense allocations for the active family workspace."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        allocs, total = await self.repo.list_allocations(
            workspace_id=context.workspace.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        responses = [self._map_allocation_to_response(a) for a in allocs]
        return responses, total

    # -------------------------------------------------------------------------
    # Member Contributions
    # -------------------------------------------------------------------------

    async def record_contribution(
        self,
        context: WorkspaceContext,
        data: RecordContributionRequest,
    ) -> FamilyContributionResponse:
        """Records an expected or paid member contribution to the household pool."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        if not context.can(Permission.MANAGE_FAMILY_CONTRIBUTIONS):
            raise InsufficientPermissionsException(message="Permission required to record contributions.")

        # Validate member belongs to family
        member = await self.repo.get_member(context.workspace.id, data.member_user_id)
        if not member:
            raise NotFoundException(message="Member not found in this family workspace.")

        status_str = "expected"
        if data.paid_amount_paise >= data.expected_amount_paise and data.expected_amount_paise > 0:
            status_str = "paid"
        elif data.paid_amount_paise > 0:
            status_str = "partially_paid"

        contribution = FamilyMemberContribution(
            workspace_id=context.workspace.id,
            member_user_id=data.member_user_id,
            period=data.period,
            contribution_type=data.contribution_type,
            expected_amount_paise=data.expected_amount_paise,
            paid_amount_paise=data.paid_amount_paise,
            currency=context.workspace.default_currency,
            due_date=data.due_date,
            status=status_str,
            recorded_transaction_id=data.recorded_transaction_id,
            notes=data.notes,
            created_by_id=context.current_user.id,
        )
        saved = await self.repo.create_contribution(contribution)

        # Log timeline
        await self.repo.record_activity(
            FamilyActivity(
                workspace_id=context.workspace.id,
                actor_user_id=context.current_user.id,
                activity_type=FamilyActivityType.CONTRIBUTION_RECORDED.value,
                resource_type="contribution",
                resource_id=str(saved.id),
                title="Household Contribution Recorded",
                description=f"Contribution for period {saved.period}: ₹{paise_to_decimal(saved.paid_amount_paise)} paid (expected: ₹{paise_to_decimal(saved.expected_amount_paise)}).",
                metadata_payload={
                    "member_user_id": str(saved.member_user_id),
                    "period": saved.period,
                    "status": saved.status,
                },
            )
        )
        await self.session.commit()
        return await self._to_contribution_response(saved.id, context.workspace.id)

    async def update_contribution(
        self,
        context: WorkspaceContext,
        contribution_id: UUID,
        data: UpdateContributionRequest,
    ) -> FamilyContributionResponse:
        """Updates a contribution's paid amount or settlement status."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        if not context.can(Permission.MANAGE_FAMILY_CONTRIBUTIONS):
            raise InsufficientPermissionsException(message="Permission required to update contributions.")

        updated = await self.repo.update_contribution(
            contribution_id=contribution_id,
            workspace_id=context.workspace.id,
            paid_amount_paise=data.paid_amount_paise,
            status=data.status,
            notes=data.notes,
        )
        if not updated:
            raise NotFoundException(message="Contribution record not found.")

        await self.repo.record_activity(
            FamilyActivity(
                workspace_id=context.workspace.id,
                actor_user_id=context.current_user.id,
                activity_type=FamilyActivityType.CONTRIBUTION_UPDATED.value,
                resource_type="contribution",
                resource_id=str(updated.id),
                title="Household Contribution Updated",
                description=f"Contribution status: {updated.status}, Paid: ₹{paise_to_decimal(updated.paid_amount_paise)}.",
                metadata_payload={"status": updated.status, "paid_amount_paise": updated.paid_amount_paise},
            )
        )
        await self.session.commit()
        return await self._to_contribution_response(updated.id, context.workspace.id)

    async def list_contributions(
        self,
        context: WorkspaceContext,
        period: Optional[str] = None,
        member_user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FamilyContributionResponse], int]:
        """Lists member contributions for active family workspace."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        contribs, total = await self.repo.list_contributions(
            workspace_id=context.workspace.id,
            period=period,
            member_user_id=member_user_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [self._map_contribution_to_response(c) for c in contribs], total

    # -------------------------------------------------------------------------
    # Settlements & Net Positions
    # -------------------------------------------------------------------------

    async def get_settlement_summary(
        self,
        context: WorkspaceContext,
        period: Optional[str] = None,
    ) -> FamilySettlementSummaryResponse:
        """
        Calculates exact net household positions and peer-to-peer settlement suggestions.
        Net Position = (expenses_paid + contributions_paid) - allocated_shares.
        """
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        expenses_paid, contribs_paid, allocated_shares = await self.repo.get_settlement_aggregation(
            workspace_id=context.workspace.id,
            period=period,
        )

        members = await self.repo.list_family_members(context.workspace.id)
        member_settlements: List[MemberSettlementResponse] = []
        member_settlements_vo = []

        total_expenses = sum(expenses_paid.values())
        total_contribs = sum(contribs_paid.values())
        total_allocated = sum(allocated_shares.values())

        for m, u in members:
            e_paid = expenses_paid.get(u.id, 0)
            c_paid = contribs_paid.get(u.id, 0)
            s_alloc = allocated_shares.get(u.id, 0)
            net_pos = (e_paid + c_paid) - s_alloc

            status_str = "settled"
            if net_pos > 0:
                status_str = "surplus"
            elif net_pos < 0:
                status_str = "deficit"

            ms_resp = MemberSettlementResponse(
                member_user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                role=m.role,
                total_expenses_paid_paise=e_paid,
                total_expenses_paid_decimal=paise_to_decimal(e_paid),
                total_contributions_paid_paise=c_paid,
                total_contributions_paid_decimal=paise_to_decimal(c_paid),
                total_allocated_share_paise=s_alloc,
                total_allocated_share_decimal=paise_to_decimal(s_alloc),
                net_position_paise=net_pos,
                net_position_decimal=paise_to_decimal(net_pos),
                currency=context.workspace.default_currency,
                status=status_str,
            )
            member_settlements.append(ms_resp)

            # VO for algorithm
            from app.domain.family import MemberSettlementVO
            member_settlements_vo.append(
                MemberSettlementVO(
                    member_user_id=u.id,
                    full_name=u.full_name,
                    email=u.email,
                    role=m.role,
                    total_expenses_paid_paise=e_paid,
                    total_contributions_paid_paise=c_paid,
                    total_allocated_share_paise=s_alloc,
                    net_position_paise=net_pos,
                    currency=context.workspace.default_currency,
                    status=status_str,
                )
            )

        recommendations_vo = compute_settlement_recommendations(member_settlements_vo)
        recommendations = [
            SettlementRecommendationResponse(
                from_member_id=r.from_member_id,
                from_member_name=r.from_member_name,
                to_member_id=r.to_member_id,
                to_member_name=r.to_member_name,
                amount_paise=r.amount_paise,
                amount_decimal=paise_to_decimal(r.amount_paise),
                currency=r.currency,
                note=r.note,
            )
            for r in recommendations_vo
        ]

        return FamilySettlementSummaryResponse(
            workspace_id=context.workspace.id,
            period=period,
            currency=context.workspace.default_currency,
            total_shared_expenses_paise=total_expenses,
            total_shared_expenses_decimal=paise_to_decimal(total_expenses),
            total_contributions_paid_paise=total_contribs,
            total_contributions_paid_decimal=paise_to_decimal(total_contribs),
            total_allocated_paise=total_allocated,
            total_allocated_decimal=paise_to_decimal(total_allocated),
            member_settlements=member_settlements,
            recommendations=recommendations,
        )

    # -------------------------------------------------------------------------
    # Shared Personal Accounts (Privacy Bridge)
    # -------------------------------------------------------------------------

    async def share_personal_account(
        self,
        context: WorkspaceContext,
        account_id: UUID,
        share_scope: str = "balance_only",
        notes: Optional[str] = None,
    ) -> SharedAccountResponse:
        """
        Selectively shares a personal account into the family workspace.
        Enforces that the caller owns the personal account.
        """
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        # Verify account ownership: must be created by or owned by context.current_user
        acc_stmt = select(Account).where(Account.id == account_id)
        acc_res = await self.session.execute(acc_stmt)
        account = acc_res.scalar_one_or_none()
        if not account:
            raise NotFoundException(message="Account not found.")

        # Anti-IDOR check: Caller must be the account creator
        if account.created_by_id != context.current_user.id:
            raise ForbiddenException(
                message="You can only share accounts that belong to your personal ownership."
            )

        # Check existing share
        existing = await self.repo.get_account_share(context.workspace.id, account_id)
        if existing:
            existing.share_scope = share_scope
            existing.is_active = True
            existing.notes = notes
            existing.updated_at = datetime.now(timezone.utc)
            share = existing
        else:
            share = FamilyAccountShare(
                family_workspace_id=context.workspace.id,
                account_id=account.id,
                shared_by_user_id=context.current_user.id,
                share_scope=share_scope,
                is_active=True,
                notes=notes,
            )
            share = await self.repo.create_account_share(share)

        await self.repo.record_activity(
            FamilyActivity(
                workspace_id=context.workspace.id,
                actor_user_id=context.current_user.id,
                activity_type=FamilyActivityType.SHARED_ACCOUNT_ADDED.value,
                resource_type="account",
                resource_id=str(account.id),
                title="Personal Account Shared with Family",
                description=f"Account '{account.name}' shared with scope '{share_scope}' by {context.current_user.full_name}.",
                metadata_payload={"account_id": str(account.id), "scope": share_scope},
            )
        )
        await self.session.commit()
        return self._map_shared_account_to_response(share, account, context.current_user)

    async def list_shared_accounts(
        self,
        context: WorkspaceContext,
    ) -> List[SharedAccountResponse]:
        """Lists personal accounts selectively shared with the family workspace."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        shares = await self.repo.list_shared_accounts(context.workspace.id, active_only=True)
        return [
            self._map_shared_account_to_response(s, s.account, s.shared_by)
            for s in shares
        ]

    async def revoke_account_share(
        self,
        context: WorkspaceContext,
        account_id: UUID,
    ) -> bool:
        """Revokes personal account sharing into the family workspace."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        share = await self.repo.get_account_share(context.workspace.id, account_id)
        if not share:
            raise NotFoundException(message="Shared account record not found.")

        # Sharer or admin can revoke
        is_sharer = (share.shared_by_user_id == context.current_user.id)
        is_admin = context.can(Permission.MANAGE_FAMILY_SETTINGS)
        if not is_sharer and not is_admin:
            raise ForbiddenException(message="Only the account sharer or family administrator can revoke access.")

        share.is_active = False
        share.updated_at = datetime.now(timezone.utc)

        await self.repo.record_activity(
            FamilyActivity(
                workspace_id=context.workspace.id,
                actor_user_id=context.current_user.id,
                activity_type=FamilyActivityType.SHARED_ACCOUNT_REVOKED.value,
                resource_type="account",
                resource_id=str(account_id),
                title="Account Sharing Revoked",
                description=f"Account sharing revoked by {context.current_user.full_name}.",
                metadata_payload={"account_id": str(account_id)},
            )
        )
        await self.session.commit()
        return True

    # -------------------------------------------------------------------------
    # Activity Timeline
    # -------------------------------------------------------------------------

    async def list_activities(
        self,
        context: WorkspaceContext,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """Lists activity timeline for the family workspace."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        activities, total = await self.repo.list_activities(
            workspace_id=context.workspace.id,
            limit=limit,
            offset=offset,
        )
        data = [
            {
                "id": a.id,
                "workspace_id": a.workspace_id,
                "actor_user_id": a.actor_user_id,
                "actor_name": a.actor.full_name if a.actor else "System",
                "activity_type": a.activity_type,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "title": a.title,
                "description": a.description,
                "metadata": a.metadata_payload,
                "created_at": a.created_at,
            }
            for a in activities
        ]
        return data, total

    # -------------------------------------------------------------------------
    # Family Overview & Dashboard
    # -------------------------------------------------------------------------

    async def get_family_overview(
        self,
        context: WorkspaceContext,
    ) -> FamilyOverviewResponse:
        """Produces a consolidated household financial dashboard overview."""
        if context.workspace.type != "family":
            raise ValidationException(message="Active workspace is not a family workspace.")

        profile_resp = await self.get_family_profile(context)
        members = await self.repo.list_family_members(context.workspace.id)

        # 1. Monthly income and expense in family workspace
        today = date.today()
        first_of_month = date(today.year, today.month, 1)

        income_stmt = select(func.coalesce(func.sum(Transaction.amount_paise), 0)).where(
            Transaction.workspace_id == context.workspace.id,
            Transaction.direction == "inflow",
            Transaction.status == "posted",
            Transaction.transaction_date >= first_of_month,
        )
        total_income_paise = (await self.session.execute(income_stmt)).scalar() or 0

        expense_stmt = select(func.coalesce(func.sum(Transaction.amount_paise), 0)).where(
            Transaction.workspace_id == context.workspace.id,
            Transaction.direction == "outflow",
            Transaction.status == "posted",
            Transaction.transaction_date >= first_of_month,
        )
        total_expense_paise = (await self.session.execute(expense_stmt)).scalar() or 0
        net_savings_paise = total_income_paise - total_expense_paise

        # 2. Shared Account Balances (Accounts belonging to family workspace + shared personal accounts)
        direct_accounts_stmt = select(func.coalesce(func.sum(Account.current_book_balance_paise), 0)).where(
            Account.workspace_id == context.workspace.id,
            Account.status == "active",
        )
        direct_balances_paise = (await self.session.execute(direct_accounts_stmt)).scalar() or 0

        shared_accounts = await self.repo.list_shared_accounts(context.workspace.id, active_only=True)
        shared_balances_paise = sum(s.account.current_book_balance_paise for s in shared_accounts if s.account)
        total_shared_balances_paise = direct_balances_paise + shared_balances_paise

        # 3. Active Budgets & Utilization
        budget_stmt = select(Budget).where(
            Budget.workspace_id == context.workspace.id,
            Budget.status == "active",
        )
        budgets_res = await self.session.execute(budget_stmt)
        active_budgets = list(budgets_res.scalars().all())
        total_budget_paise = sum(b.total_allocated_paise for b in active_budgets)

        utilization_pct = Decimal("0.00")
        if total_budget_paise > 0:
            utilization_pct = (Decimal(total_expense_paise) / Decimal(total_budget_paise) * Decimal(100)).quantize(Decimal("0.01"))

        # 4. Goals and Commitments counts
        goals_stmt = select(func.count(FinancialGoal.id)).where(
            FinancialGoal.workspace_id == context.workspace.id,
            FinancialGoal.status == "active",
        )
        active_goals_count = (await self.session.execute(goals_stmt)).scalar() or 0

        recurr_stmt = select(func.count(RecurringDefinition.id)).where(
            RecurringDefinition.workspace_id == context.workspace.id,
            RecurringDefinition.status == "active",
        )
        upcoming_commitments_count = (await self.session.execute(recurr_stmt)).scalar() or 0

        # 5. Top Expense Categories
        from app.infrastructure.database.models.category import Category
        cat_stmt = (
            select(
                func.coalesce(Category.name, "Uncategorized").label("category_name"),
                func.sum(Transaction.amount_paise).label("total_paise"),
            )
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.workspace_id == context.workspace.id,
                Transaction.direction == "outflow",
                Transaction.status == "posted",
                Transaction.transaction_date >= first_of_month,
            )
            .group_by(Category.name)
            .order_by(desc("total_paise"))
            .limit(5)
        )
        cat_res = await self.session.execute(cat_stmt)
        top_cats = [
            {
                "category": row.category_name,
                "amount_paise": row.total_paise,
                "amount_decimal": paise_to_decimal(row.total_paise),
            }
            for row in cat_res.all()
        ]

        # 6. Recent Shared Transactions
        recent_tx_stmt = (
            select(Transaction)
            .options(selectinload(Transaction.created_by))
            .where(
                Transaction.workspace_id == context.workspace.id,
                Transaction.status == "posted",
            )
            .order_by(desc(Transaction.transaction_date), desc(Transaction.created_at))
            .limit(5)
        )
        recent_tx_res = await self.session.execute(recent_tx_stmt)
        recent_txs = [
            {
                "id": str(t.id),
                "description": t.description,
                "amount_paise": t.amount_paise,
                "amount_decimal": paise_to_decimal(t.amount_paise),
                "currency": t.currency,
                "direction": t.direction,
                "transaction_date": str(t.transaction_date),
                "paid_by": t.created_by.full_name if t.created_by else "Unknown",
            }
            for t in recent_tx_res.scalars().all()
        ]

        return FamilyOverviewResponse(
            profile=profile_resp,
            member_count=len(members),
            total_household_income_paise=total_income_paise,
            total_household_income_decimal=paise_to_decimal(total_income_paise),
            total_household_expense_paise=total_expense_paise,
            total_household_expense_decimal=paise_to_decimal(total_expense_paise),
            net_household_savings_paise=net_savings_paise,
            net_household_savings_decimal=paise_to_decimal(net_savings_paise),
            shared_account_balances_paise=total_shared_balances_paise,
            shared_account_balances_decimal=paise_to_decimal(total_shared_balances_paise),
            budget_utilization_pct=utilization_pct,
            active_budgets_count=len(active_budgets),
            active_goals_count=active_goals_count,
            upcoming_commitments_count=upcoming_commitments_count,
            top_expense_categories=top_cats,
            recent_shared_transactions=recent_txs,
        )

    # -------------------------------------------------------------------------
    # Response Mappers (Internal Helpers)
    # -------------------------------------------------------------------------

    async def _to_allocation_response(self, alloc_id: UUID, workspace_id: UUID) -> FamilyAllocationResponse:
        alloc = await self.repo.get_allocation_by_id(alloc_id, workspace_id)
        if not alloc:
            raise NotFoundException(message="Allocation not found.")
        return self._map_allocation_to_response(alloc)

    def _map_allocation_to_response(self, alloc: FamilyExpenseAllocation) -> FamilyAllocationResponse:
        items_resp = [
            AllocationItemResponse(
                id=it.id,
                member_user_id=it.member_user_id,
                member_name=it.member.full_name if it.member else None,
                assigned_share_paise=it.assigned_share_paise,
                assigned_share_decimal=paise_to_decimal(it.assigned_share_paise),
                percentage=it.percentage,
                is_paid_by=it.is_paid_by,
                settlement_status=it.settlement_status,
                notes=it.notes,
            )
            for it in alloc.items
        ]
        return FamilyAllocationResponse(
            id=alloc.id,
            workspace_id=alloc.workspace_id,
            transaction_id=alloc.transaction_id,
            transaction_description=alloc.transaction.description if alloc.transaction else None,
            allocation_method=alloc.allocation_method,
            total_amount_paise=alloc.total_amount_paise,
            total_amount_decimal=paise_to_decimal(alloc.total_amount_paise),
            currency=alloc.currency,
            status=alloc.status,
            version=alloc.version,
            notes=alloc.notes,
            items=items_resp,
            created_at=alloc.created_at,
        )

    async def _to_contribution_response(self, contrib_id: UUID, workspace_id: UUID) -> FamilyContributionResponse:
        c = await self.repo.get_contribution_by_id(contrib_id, workspace_id)
        if not c:
            raise NotFoundException(message="Contribution not found.")
        return self._map_contribution_to_response(c)

    def _map_contribution_to_response(self, c: FamilyMemberContribution) -> FamilyContributionResponse:
        return FamilyContributionResponse(
            id=c.id,
            workspace_id=c.workspace_id,
            member_user_id=c.member_user_id,
            member_name=c.member.full_name if c.member else None,
            period=c.period,
            contribution_type=c.contribution_type,
            expected_amount_paise=c.expected_amount_paise,
            expected_amount_decimal=paise_to_decimal(c.expected_amount_paise),
            paid_amount_paise=c.paid_amount_paise,
            paid_amount_decimal=paise_to_decimal(c.paid_amount_paise),
            currency=c.currency,
            due_date=c.due_date,
            status=c.status,
            notes=c.notes,
            created_at=c.created_at,
        )

    def _map_shared_account_to_response(
        self,
        share: FamilyAccountShare,
        account: Account,
        user: User,
    ) -> SharedAccountResponse:
        return SharedAccountResponse(
            id=share.id,
            family_workspace_id=share.family_workspace_id,
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            masked_identifier=account.masked_identifier,
            shared_by_user_id=user.id,
            shared_by_name=user.full_name,
            share_scope=share.share_scope,
            current_balance_paise=account.current_book_balance_paise,
            current_balance_decimal=paise_to_decimal(account.current_book_balance_paise),
            currency=account.currency,
            is_active=share.is_active,
            created_at=share.created_at,
        )
