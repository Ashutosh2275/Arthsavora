"""
Arthsavora Family Finance Repository
Database access patterns for family profiles, expense allocations, member contributions,
shared personal accounts, and activity timeline with strict workspace scoping.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.family import (
    FamilyAccountShare,
    FamilyActivity,
    FamilyExpenseAllocation,
    FamilyExpenseAllocationItem,
    FamilyMemberContribution,
    FamilyProfile,
)
from app.infrastructure.database.models.transaction import Transaction
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import WorkspaceMember


class FamilyRepository:
    """Repository handling persistence and aggregation for collaborative family finance."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Profile & Preferences
    # -------------------------------------------------------------------------

    async def get_or_create_profile(
        self,
        workspace_id: UUID,
        default_name: str = "Household",
        currency: str = "INR",
        timezone_str: str = "Asia/Kolkata",
    ) -> FamilyProfile:
        """Retrieves or creates initial family profile configuration."""
        stmt = select(FamilyProfile).where(FamilyProfile.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            profile = FamilyProfile(
                workspace_id=workspace_id,
                household_name=default_name,
                household_currency=currency,
                household_timezone=timezone_str,
                monthly_budget_start_day=1,
                default_allocation_method="equal",
                contribution_reminder_day=25,
                enable_shared_budget_alerts=True,
                enable_contribution_reminders=True,
                settings={},
            )
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)

        return profile

    async def update_profile(
        self,
        workspace_id: UUID,
        update_data: dict,
    ) -> Optional[FamilyProfile]:
        """Updates family profile preferences."""
        stmt = select(FamilyProfile).where(FamilyProfile.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return None

        for k, v in update_data.items():
            if hasattr(profile, k) and v is not None:
                setattr(profile, k, v)

        profile.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    # -------------------------------------------------------------------------
    # Members
    # -------------------------------------------------------------------------

    async def list_family_members(
        self,
        workspace_id: UUID,
    ) -> List[Tuple[WorkspaceMember, User]]:
        """Returns all active workspace members with joined User details."""
        stmt = (
            select(WorkspaceMember, User)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.status == "active",
            )
            .order_by(WorkspaceMember.joined_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.all())

    async def get_member(
        self,
        workspace_id: UUID,
        member_user_id: UUID,
    ) -> Optional[WorkspaceMember]:
        """Retrieves an active membership record."""
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == member_user_id,
            WorkspaceMember.status == "active",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # Expense Allocations
    # -------------------------------------------------------------------------

    async def create_allocation(
        self,
        allocation: FamilyExpenseAllocation,
    ) -> FamilyExpenseAllocation:
        """Saves an expense allocation and its child allocation items."""
        self.db.add(allocation)
        await self.db.flush()
        await self.db.refresh(allocation)
        return allocation

    async def get_allocation_by_id(
        self,
        allocation_id: UUID,
        workspace_id: UUID,
    ) -> Optional[FamilyExpenseAllocation]:
        """Fetches an allocation with its items and transaction."""
        stmt = (
            select(FamilyExpenseAllocation)
            .options(
                selectinload(FamilyExpenseAllocation.items).selectinload(FamilyExpenseAllocationItem.member),
                selectinload(FamilyExpenseAllocation.transaction),
                selectinload(FamilyExpenseAllocation.created_by),
            )
            .where(
                FamilyExpenseAllocation.id == allocation_id,
                FamilyExpenseAllocation.workspace_id == workspace_id,
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_allocation_by_transaction_id(
        self,
        transaction_id: UUID,
        workspace_id: UUID,
    ) -> Optional[FamilyExpenseAllocation]:
        """Retrieves active allocation associated with a transaction."""
        stmt = (
            select(FamilyExpenseAllocation)
            .options(
                selectinload(FamilyExpenseAllocation.items).selectinload(FamilyExpenseAllocationItem.member),
                selectinload(FamilyExpenseAllocation.transaction),
            )
            .where(
                FamilyExpenseAllocation.transaction_id == transaction_id,
                FamilyExpenseAllocation.workspace_id == workspace_id,
                FamilyExpenseAllocation.status == "active",
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_allocations(
        self,
        workspace_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FamilyExpenseAllocation], int]:
        """Paginated list of allocations for a family workspace."""
        query = select(FamilyExpenseAllocation).where(
            FamilyExpenseAllocation.workspace_id == workspace_id
        )
        if status:
            query = query.where(FamilyExpenseAllocation.status == status)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        fetch_stmt = (
            query.options(
                selectinload(FamilyExpenseAllocation.items).selectinload(FamilyExpenseAllocationItem.member),
                selectinload(FamilyExpenseAllocation.transaction),
            )
            .order_by(desc(FamilyExpenseAllocation.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(fetch_stmt)
        return list(res.scalars().all()), total

    # -------------------------------------------------------------------------
    # Member Contributions
    # -------------------------------------------------------------------------

    async def create_contribution(
        self,
        contribution: FamilyMemberContribution,
    ) -> FamilyMemberContribution:
        """Saves a member contribution record."""
        self.db.add(contribution)
        await self.db.flush()
        await self.db.refresh(contribution)
        return contribution

    async def get_contribution_by_id(
        self,
        contribution_id: UUID,
        workspace_id: UUID,
    ) -> Optional[FamilyMemberContribution]:
        """Retrieves contribution with member details."""
        stmt = (
            select(FamilyMemberContribution)
            .options(
                selectinload(FamilyMemberContribution.member),
                selectinload(FamilyMemberContribution.created_by),
                selectinload(FamilyMemberContribution.recorded_transaction),
            )
            .where(
                FamilyMemberContribution.id == contribution_id,
                FamilyMemberContribution.workspace_id == workspace_id,
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_contributions(
        self,
        workspace_id: UUID,
        period: Optional[str] = None,
        member_user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FamilyMemberContribution], int]:
        """Lists member contributions filtered by period or member."""
        query = select(FamilyMemberContribution).where(
            FamilyMemberContribution.workspace_id == workspace_id
        )
        if period:
            query = query.where(FamilyMemberContribution.period == period)
        if member_user_id:
            query = query.where(FamilyMemberContribution.member_user_id == member_user_id)
        if status:
            query = query.where(FamilyMemberContribution.status == status)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        fetch_stmt = (
            query.options(
                selectinload(FamilyMemberContribution.member),
                selectinload(FamilyMemberContribution.recorded_transaction),
            )
            .order_by(desc(FamilyMemberContribution.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(fetch_stmt)
        return list(res.scalars().all()), total

    async def update_contribution(
        self,
        contribution_id: UUID,
        workspace_id: UUID,
        paid_amount_paise: Optional[int] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[FamilyMemberContribution]:
        """Updates a contribution's paid amount or lifecycle status."""
        contrib = await self.get_contribution_by_id(contribution_id, workspace_id)
        if not contrib:
            return None

        if paid_amount_paise is not None:
            contrib.paid_amount_paise = paid_amount_paise
            if paid_amount_paise >= contrib.expected_amount_paise and contrib.expected_amount_paise > 0:
                contrib.status = "paid"
            elif paid_amount_paise > 0:
                contrib.status = "partially_paid"

        if status is not None:
            contrib.status = status

        if notes is not None:
            contrib.notes = notes

        contrib.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(contrib)
        return contrib

    # -------------------------------------------------------------------------
    # Shared Personal Accounts (Bridge)
    # -------------------------------------------------------------------------

    async def create_account_share(
        self,
        share: FamilyAccountShare,
    ) -> FamilyAccountShare:
        """Shares a personal account into a family workspace."""
        self.db.add(share)
        await self.db.flush()
        await self.db.refresh(share)
        return share

    async def get_account_share(
        self,
        family_workspace_id: UUID,
        account_id: UUID,
    ) -> Optional[FamilyAccountShare]:
        """Checks if an account is shared with the family workspace."""
        stmt = (
            select(FamilyAccountShare)
            .options(
                selectinload(FamilyAccountShare.account),
                selectinload(FamilyAccountShare.shared_by),
            )
            .where(
                FamilyAccountShare.family_workspace_id == family_workspace_id,
                FamilyAccountShare.account_id == account_id,
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_shared_accounts(
        self,
        family_workspace_id: UUID,
        active_only: bool = True,
    ) -> List[FamilyAccountShare]:
        """Lists personal accounts shared with the family workspace."""
        query = (
            select(FamilyAccountShare)
            .options(
                selectinload(FamilyAccountShare.account),
                selectinload(FamilyAccountShare.shared_by),
            )
            .where(FamilyAccountShare.family_workspace_id == family_workspace_id)
        )
        if active_only:
            query = query.where(FamilyAccountShare.is_active.is_(True))

        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def revoke_account_share(
        self,
        family_workspace_id: UUID,
        account_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Revokes account sharing (only account sharer or workspace admin can revoke)."""
        stmt = select(FamilyAccountShare).where(
            FamilyAccountShare.family_workspace_id == family_workspace_id,
            FamilyAccountShare.account_id == account_id,
        )
        res = await self.db.execute(stmt)
        share = res.scalar_one_or_none()
        if not share:
            return False

        share.is_active = False
        share.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    # -------------------------------------------------------------------------
    # Activity Timeline
    # -------------------------------------------------------------------------

    async def record_activity(
        self,
        activity: FamilyActivity,
    ) -> FamilyActivity:
        """Records an auditable event to the family activity stream."""
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def list_activities(
        self,
        workspace_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FamilyActivity], int]:
        """Lists timeline activity for a family workspace."""
        query = select(FamilyActivity).where(FamilyActivity.workspace_id == workspace_id)
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        fetch_stmt = (
            query.options(selectinload(FamilyActivity.actor))
            .order_by(desc(FamilyActivity.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(fetch_stmt)
        return list(res.scalars().all()), total

    # -------------------------------------------------------------------------
    # Settlement Aggregation
    # -------------------------------------------------------------------------

    async def get_settlement_aggregation(
        self,
        workspace_id: UUID,
        period: Optional[str] = None,
    ) -> Tuple[Dict[UUID, int], Dict[UUID, int], Dict[UUID, int]]:
        """
        Aggregates financial inputs for net settlement calculation:
        1. expenses_paid_by_member: Sum of active shared family expenses paid by each member.
        2. contributions_paid_by_member: Sum of confirmed pool contributions paid by each member.
        3. allocated_shares_by_member: Sum of active expense allocation shares assigned to each member.
        """
        # 1. Expenses paid by member
        # In family allocations, items with is_paid_by=True represent the member who paid the bill.
        # Alternatively, if not allocated, transaction created_by_id paid.
        expenses_paid: Dict[UUID, int] = {}
        alloc_payer_stmt = (
            select(
                FamilyExpenseAllocationItem.member_user_id,
                func.sum(FamilyExpenseAllocation.total_amount_paise).label("paid_total"),
            )
            .join(
                FamilyExpenseAllocation,
                FamilyExpenseAllocationItem.allocation_id == FamilyExpenseAllocation.id,
            )
            .where(
                FamilyExpenseAllocation.workspace_id == workspace_id,
                FamilyExpenseAllocation.status == "active",
                FamilyExpenseAllocationItem.is_paid_by.is_(True),
            )
            .group_by(FamilyExpenseAllocationItem.member_user_id)
        )
        alloc_res = await self.db.execute(alloc_payer_stmt)
        for m_id, paid_total in alloc_res.all():
            expenses_paid[m_id] = int(paid_total or 0)

        # 2. Contributions paid by member
        contributions_paid: Dict[UUID, int] = {}
        contrib_query = (
            select(
                FamilyMemberContribution.member_user_id,
                func.sum(FamilyMemberContribution.paid_amount_paise).label("contrib_total"),
            )
            .where(
                FamilyMemberContribution.workspace_id == workspace_id,
                FamilyMemberContribution.status.in_(["paid", "partially_paid"]),
            )
        )
        if period:
            contrib_query = contrib_query.where(FamilyMemberContribution.period == period)
        contrib_query = contrib_query.group_by(FamilyMemberContribution.member_user_id)

        contrib_res = await self.db.execute(contrib_query)
        for m_id, contrib_total in contrib_res.all():
            contributions_paid[m_id] = int(contrib_total or 0)

        # 3. Allocated shares assigned to member
        allocated_shares: Dict[UUID, int] = {}
        shares_stmt = (
            select(
                FamilyExpenseAllocationItem.member_user_id,
                func.sum(FamilyExpenseAllocationItem.assigned_share_paise).label("share_total"),
            )
            .join(
                FamilyExpenseAllocation,
                FamilyExpenseAllocationItem.allocation_id == FamilyExpenseAllocation.id,
            )
            .where(
                FamilyExpenseAllocation.workspace_id == workspace_id,
                FamilyExpenseAllocation.status == "active",
            )
            .group_by(FamilyExpenseAllocationItem.member_user_id)
        )
        shares_res = await self.db.execute(shares_stmt)
        for m_id, share_total in shares_res.all():
            allocated_shares[m_id] = int(share_total or 0)

        return expenses_paid, contributions_paid, allocated_shares
