"""
Arthsavora Family Finance & Collaborative Household Budgeting Test Suite
Comprehensive validation of pure domain allocation math, deterministic remainder distribution,
member roles, privacy boundaries, personal account sharing, settlement calculations,
REST API endpoints, and AI Assistant tool orchestration.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, InsufficientPermissionsException, NotFoundException, ValidationException
from app.core.permissions import Permission, WorkspaceContext
from app.core.security import create_access_token
from app.domain.family import (
    AllocationMethod,
    AllocationStatus,
    calculate_custom_allocation,
    calculate_equal_allocation,
    calculate_fixed_allocation,
    calculate_percentage_allocation,
    compute_settlement_recommendations,
    is_resource_accessible_in_family,
    MemberSettlementVO,
)
from app.infrastructure.database.models import User, Workspace, WorkspaceMember, WorkspaceRole
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.family import (
    FamilyAccountShare,
    FamilyExpenseAllocation,
    FamilyExpenseAllocationItem,
    FamilyMemberContribution,
    FamilyProfile,
)
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.family_repository import FamilyRepository
from app.schemas.family_schema import (
    CreateAllocationRequest,
    RecordContributionRequest,
    UpdateFamilyProfileRequest,
)
from app.domain.assistant import ToolCallVO
from app.services.assistant.tool_executor import ToolExecutor
from app.services.family_service import FamilyService


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
async def setup_family_workspace(db_session: AsyncSession):
    """Sets up a family workspace with an owner (User A) and adult member (User B)."""
    # 1. Owner (User A)
    user_a_id = uuid.uuid4()
    user_a = User(
        id=user_a_id,
        email=f"family_owner_{user_a_id.hex[:6]}@arthsavora.com",
        full_name="Rajesh Sharma",
        is_active=True,
    )
    db_session.add(user_a)

    # 2. Member (User B)
    user_b_id = uuid.uuid4()
    user_b = User(
        id=user_b_id,
        email=f"family_member_{user_b_id.hex[:6]}@arthsavora.com",
        full_name="Pooja Sharma",
        is_active=True,
    )
    db_session.add(user_b)

    # 3. Restricted Member (User C / Teen)
    user_c_id = uuid.uuid4()
    user_c = User(
        id=user_c_id,
        email=f"family_teen_{user_c_id.hex[:6]}@arthsavora.com",
        full_name="Aarav Sharma",
        is_active=True,
    )
    db_session.add(user_c)

    # 4. Family Workspace
    fam_ws_id = uuid.uuid4()
    family_ws = Workspace(
        id=fam_ws_id,
        name="Sharma Household",
        slug=f"sharma-household-{fam_ws_id.hex[:6]}",
        type="family",
        owner_id=user_a_id,
        default_currency="INR",
        timezone="Asia/Kolkata",
    )
    db_session.add(family_ws)

    # Memberships
    mem_a = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=fam_ws_id,
        user_id=user_a_id,
        role=WorkspaceRole.OWNER,
    )
    mem_b = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=fam_ws_id,
        user_id=user_b_id,
        role=WorkspaceRole.MEMBER,
    )
    mem_c = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=fam_ws_id,
        user_id=user_c_id,
        role=WorkspaceRole.RESTRICTED,
    )
    db_session.add_all([mem_a, mem_b, mem_c])

    # 5. Shared Bank Account in Family Workspace
    shared_acc = Account(
        id=uuid.uuid4(),
        workspace_id=fam_ws_id,
        name="HDFC Joint Household Account",
        account_type="savings",
        currency="INR",
        current_book_balance_paise=5000000,  # ₹50,000.00
        status="active",
        created_by_id=user_a_id,
    )
    db_session.add(shared_acc)

    # 6. User B's Private Personal Workspace and Account (for privacy testing)
    personal_ws_b_id = uuid.uuid4()
    personal_ws_b = Workspace(
        id=personal_ws_b_id,
        name="Pooja Personal",
        slug=f"pooja-personal-{personal_ws_b_id.hex[:6]}",
        type="personal",
        owner_id=user_b_id,
    )
    db_session.add(personal_ws_b)

    mem_personal_b = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=personal_ws_b_id,
        user_id=user_b_id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(mem_personal_b)

    private_acc_b = Account(
        id=uuid.uuid4(),
        workspace_id=personal_ws_b_id,
        name="Pooja Private Salary Account",
        account_type="salary",
        currency="INR",
        current_book_balance_paise=12000000,  # ₹1,20,000.00
        status="active",
        created_by_id=user_b_id,
    )
    db_session.add(private_acc_b)

    await db_session.commit()
    return {
        "user_a": user_a,
        "user_b": user_b,
        "user_c": user_c,
        "family_ws": family_ws,
        "shared_acc": shared_acc,
        "personal_ws_b": personal_ws_b,
        "private_acc_b": private_acc_b,
        "mem_a": mem_a,
        "mem_b": mem_b,
        "mem_c": mem_c,
    }


# -----------------------------------------------------------------------------
# 1. Pure Domain Math & Allocation Tests
# -----------------------------------------------------------------------------

def test_domain_equal_allocation_exact_paise():
    """Verifies that equal allocation splits odd amounts deterministically with zero paise lost."""
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    # ₹100.00 (10,000 paise) among 3 members: 10000 // 3 = 3333 with 1 remainder
    # Payer gets the extra 1 paise
    items = calculate_equal_allocation(
        total_amount_paise=10000,
        member_user_ids=[u1, u2, u3],
        payer_user_id=u2,
    )

    assert len(items) == 3
    assert sum(it.assigned_share_paise for it in items) == 10000

    shares = {it.member_user_id: it.assigned_share_paise for it in items}
    assert shares[u2] == 3334
    assert shares[u1] == 3333
    assert shares[u3] == 3333


def test_domain_percentage_allocation():
    """Verifies percentage allocation handles minor units and rounding discrepancies."""
    u1, u2 = uuid.uuid4(), uuid.uuid4()

    # ₹3,550.75 (355,075 paise) split 60% / 40%
    items = calculate_percentage_allocation(
        total_amount_paise=355075,
        member_percentages={u1: Decimal("60.00"), u2: Decimal("40.00")},
    )

    assert len(items) == 2
    assert sum(it.assigned_share_paise for it in items) == 355075

    shares = {it.member_user_id: it.assigned_share_paise for it in items}
    assert shares[u1] == 213045
    assert shares[u2] == 142030


def test_domain_percentage_allocation_invalid_sum():
    """Rejects percentage allocations that do not sum to 100.00%."""
    u1, u2 = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(ValueError, match="Percentages must sum to 100.00%"):
        calculate_percentage_allocation(
            total_amount_paise=10000,
            member_percentages={u1: Decimal("50.00"), u2: Decimal("45.00")},
        )


def test_domain_fixed_allocation_validation():
    """Verifies that fixed allocations validate exact total matches and reject discrepancies."""
    u1, u2 = uuid.uuid4(), uuid.uuid4()

    # Valid exact match
    items = calculate_fixed_allocation(
        total_amount_paise=50000,
        member_shares_paise={u1: 30000, u2: 20000},
    )
    assert len(items) == 2
    assert sum(it.assigned_share_paise for it in items) == 50000

    # Discrepancy mismatch
    with pytest.raises(ValueError, match="Sum of fixed member shares"):
        calculate_fixed_allocation(
            total_amount_paise=50000,
            member_shares_paise={u1: 30000, u2: 15000},
        )


def test_domain_net_settlement_and_recommendations():
    """
    Tests settlement netting algorithm:
    Alice paid ₹6,000 for groceries. Allocated ₹3,000 to Bob.
    Bob contributed ₹1,000 to pool.
    Alice: Paid ₹6,000, Share ₹3,000 -> Net +₹3,000 (Surplus)
    Bob: Paid ₹1,000, Share ₹3,000 -> Net -₹2,000 (Deficit)
    Household pool has ₹1,000 balance.
    Recommendation: Bob should settle ₹2,000 to Alice.
    """
    alice_id, bob_id = uuid.uuid4(), uuid.uuid4()

    settlements = [
        MemberSettlementVO(
            member_user_id=alice_id,
            full_name="Alice",
            email="alice@example.com",
            role="owner",
            total_expenses_paid_paise=600000,
            total_contributions_paid_paise=0,
            total_allocated_share_paise=300000,
            net_position_paise=300000,
            status="surplus",
        ),
        MemberSettlementVO(
            member_user_id=bob_id,
            full_name="Bob",
            email="bob@example.com",
            role="member",
            total_expenses_paid_paise=0,
            total_contributions_paid_paise=100000,
            total_allocated_share_paise=300000,
            net_position_paise=-200000,
            status="deficit",
        ),
    ]

    recs = compute_settlement_recommendations(settlements)
    assert len(recs) == 1
    assert recs[0].from_member_id == bob_id
    assert recs[0].to_member_id == alice_id
    assert recs[0].amount_paise == 200000


def test_domain_zero_trust_privacy_boundary():
    """Verifies that private personal workspace resources are blocked from family access."""
    fam_ws_id = uuid.uuid4()
    personal_ws_id = uuid.uuid4()
    private_acc_id = uuid.uuid4()
    shared_acc_id = uuid.uuid4()

    # 1. Family resource is accessible
    assert is_resource_accessible_in_family(fam_ws_id, fam_ws_id) is True

    # 2. Personal resource without sharing is strictly inaccessible
    assert is_resource_accessible_in_family(personal_ws_id, fam_ws_id) is False

    # 3. Personal resource with explicit sharing is accessible
    assert is_resource_accessible_in_family(
        personal_ws_id, fam_ws_id, shared_account_ids={shared_acc_id}, target_account_id=shared_acc_id
    ) is True
    assert is_resource_accessible_in_family(
        personal_ws_id, fam_ws_id, shared_account_ids={shared_acc_id}, target_account_id=private_acc_id
    ) is False


# -----------------------------------------------------------------------------
# 2. Service & Repository Integration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_family_profile_lifecycle(db_session: AsyncSession, setup_family_workspace):
    """Verifies family profile provisioning and preference updating."""
    data = setup_family_workspace
    service = FamilyService(db_session)

    context = WorkspaceContext(
        workspace=data["family_ws"],
        membership=data["mem_a"],
        current_user=data["user_a"],
        role=WorkspaceRole.OWNER,
    )

    # 1. Fetch profile (creates defaults)
    profile = await service.get_family_profile(context)
    assert profile.household_name == "Sharma Household"
    assert profile.household_currency == "INR"
    assert profile.default_allocation_method == "equal"

    # 2. Update profile
    updated = await service.update_family_profile(
        context,
        UpdateFamilyProfileRequest(
            household_name="The Sharma Residence",
            contribution_reminder_day=28,
            default_allocation_method="percentage",
        ),
    )
    assert updated.household_name == "The Sharma Residence"
    assert updated.contribution_reminder_day == 28
    assert updated.default_allocation_method == "percentage"


@pytest.mark.asyncio
async def test_expense_allocation_service_and_revision(db_session: AsyncSession, setup_family_workspace):
    """Verifies expense allocation creation and auditable version revision."""
    data = setup_family_workspace
    service = FamilyService(db_session)

    # Create a shared expense transaction in family workspace
    tx = Transaction(
        id=uuid.uuid4(),
        workspace_id=data["family_ws"].id,
        account_id=data["shared_acc"].id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("3000.00"),
        amount_paise=300000,
        currency="INR",
        transaction_date=date.today(),
        description="BigBasket Weekly Groceries",
        status="posted",
        created_by_id=data["user_a"].id,
    )
    db_session.add(tx)
    await db_session.commit()

    context = WorkspaceContext(
        workspace=data["family_ws"],
        membership=data["mem_a"],
        current_user=data["user_a"],
        role=WorkspaceRole.OWNER,
    )

    # 1. Equal Allocation among User A and User B
    req = CreateAllocationRequest(
        transaction_id=tx.id,
        allocation_method="equal",
        member_user_ids=[data["user_a"].id, data["user_b"].id],
        notes="Groceries split 50/50",
    )
    alloc = await service.create_expense_allocation(context, req)

    assert alloc.version == 1
    assert alloc.status == "active"
    assert alloc.total_amount_paise == 300000
    assert len(alloc.items) == 2
    assert alloc.items[0].assigned_share_paise == 150000
    assert alloc.items[1].assigned_share_paise == 150000

    # 2. Revise Allocation to Percentage (70% / 30%)
    revise_req = CreateAllocationRequest(
        transaction_id=tx.id,
        allocation_method="percentage",
        member_percentages={
            str(data["user_a"].id): Decimal("70.00"),
            str(data["user_b"].id): Decimal("30.00"),
        },
        notes="Revised to 70/30 split",
    )
    revised = await service.create_expense_allocation(context, revise_req)

    assert revised.version == 2
    assert revised.status == "active"
    assert len(revised.items) == 2

    shares = {it.member_user_id: it.assigned_share_paise for it in revised.items}
    assert shares[data["user_a"].id] == 210000
    assert shares[data["user_b"].id] == 90000


@pytest.mark.asyncio
async def test_member_contributions_and_settlement(db_session: AsyncSession, setup_family_workspace):
    """Verifies pool contribution lifecycle and settlement netting."""
    data = setup_family_workspace
    service = FamilyService(db_session)

    context = WorkspaceContext(
        workspace=data["family_ws"],
        membership=data["mem_a"],
        current_user=data["user_a"],
        role=WorkspaceRole.OWNER,
    )

    # 1. Record Pool Contribution for User B
    contrib = await service.record_contribution(
        context,
        RecordContributionRequest(
            member_user_id=data["user_b"].id,
            period="2026-11",
            contribution_type="monthly",
            expected_amount_paise=2500000,  # ₹25,000 expected
            paid_amount_paise=2500000,      # ₹25,000 paid
        ),
    )
    assert contrib.status == "paid"
    assert contrib.paid_amount_paise == 2500000

    # 2. Calculate settlements
    settlement = await service.get_settlement_summary(context, period="2026-11")
    assert settlement.total_contributions_paid_paise == 2500000

    # Find User B standing
    b_standing = next(s for s in settlement.member_settlements if s.member_user_id == data["user_b"].id)
    assert b_standing.total_contributions_paid_paise == 2500000


@pytest.mark.asyncio
async def test_personal_account_sharing_privacy_bridge(db_session: AsyncSession, setup_family_workspace):
    """
    Verifies selective sharing of personal accounts:
    - User B shares personal salary account into family workspace with 'balance_only' scope.
    - User A cannot share User B's personal account (Anti-IDOR rejection).
    """
    data = setup_family_workspace
    service = FamilyService(db_session)

    context_b = WorkspaceContext(
        workspace=data["family_ws"],
        membership=data["mem_b"],
        current_user=data["user_b"],
        role=WorkspaceRole.MEMBER,
    )

    # 1. User B shares her private salary account
    shared = await service.share_personal_account(
        context=context_b,
        account_id=data["private_acc_b"].id,
        share_scope="balance_only",
        notes="Shared for household emergency buffer visibility",
    )
    assert shared.share_scope == "balance_only"
    assert shared.current_balance_paise == 12000000
    assert shared.is_active is True

    # 2. User A attempts to share User B's private account -> Forbidden
    context_a = WorkspaceContext(
        workspace=data["family_ws"],
        membership=data["mem_a"],
        current_user=data["user_a"],
        role=WorkspaceRole.OWNER,
    )
    with pytest.raises(ForbiddenException, match="personal ownership"):
        await service.share_personal_account(
            context=context_a,
            account_id=data["private_acc_b"].id,
        )


@pytest.mark.asyncio
async def test_restricted_member_privilege_enforcement(db_session: AsyncSession, setup_family_workspace):
    """Verifies that restricted members (teens/dependents) are blocked from mutating family settings."""
    data = setup_family_workspace
    service = FamilyService(db_session)

    context_c = WorkspaceContext(
        workspace=data["family_ws"],
        membership=data["mem_c"],
        current_user=data["user_c"],
        role=WorkspaceRole.RESTRICTED,
    )

    # Restricted member attempts to update family preferences -> InsufficientPermissions
    with pytest.raises(InsufficientPermissionsException):
        await service.update_family_profile(
            context_c,
            UpdateFamilyProfileRequest(household_name="Hacked Household"),
        )


# -----------------------------------------------------------------------------
# 3. REST API Endpoints Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_family_endpoints(client: AsyncClient, setup_family_workspace):
    """Tests /api/v1/family REST endpoints with authenticated workspace headers."""
    data = setup_family_workspace
    token_a = create_access_token(subject=str(data["user_a"].id), email=data["user_a"].email)
    headers = {
        "Authorization": f"Bearer {token_a}",
        "X-Workspace-ID": str(data["family_ws"].id),
    }

    # 1. GET /api/v1/family/overview
    res_overview = await client.get("/api/v1/family/overview", headers=headers)
    assert res_overview.status_code == 200
    overview_body = res_overview.json()
    assert overview_body["profile"]["household_name"] == "Sharma Household"
    assert overview_body["member_count"] == 3

    # 2. GET /api/v1/family/members
    res_members = await client.get("/api/v1/family/members", headers=headers)
    assert res_members.status_code == 200
    members_body = res_members.json()
    assert len(members_body) == 3

    # 3. GET /api/v1/family/settlements
    res_settlements = await client.get("/api/v1/family/settlements", headers=headers)
    assert res_settlements.status_code == 200
    assert "member_settlements" in res_settlements.json()


# -----------------------------------------------------------------------------
# 4. AI Assistant Tool Orchestration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_assistant_family_tools(db_session: AsyncSession, setup_family_workspace):
    """Verifies that the AI Assistant can execute family tools within verified workspace context."""
    data = setup_family_workspace
    executor = ToolExecutor(db_session)
    perms = {Permission.VIEW_FAMILY_FINANCE.value}

    # 1. Execute get_family_overview
    tc_overview = ToolCallVO(
        call_id="call-1",
        tool_name="get_family_overview",
        arguments={},
    )
    res_overview = await executor.execute_tool(
        tool_call=tc_overview,
        workspace_id=data["family_ws"].id,
        user_permissions=perms,
        user_id=data["user_a"].id,
    )
    assert res_overview.success is True
    assert res_overview.data["profile"]["household_name"] == "Sharma Household"

    # 2. Execute get_family_settlement_summary
    tc_settlement = ToolCallVO(
        call_id="call-2",
        tool_name="get_family_settlement_summary",
        arguments={"period": "2026-11"},
    )
    res_settlement = await executor.execute_tool(
        tool_call=tc_settlement,
        workspace_id=data["family_ws"].id,
        user_permissions=perms,
        user_id=data["user_a"].id,
    )
    assert res_settlement.success is True
    assert "member_settlements" in res_settlement.data

    # 3. Verify privacy boundary: Calling family tool in a personal workspace fails gracefully
    res_fail = await executor.execute_tool(
        tool_call=tc_overview,
        workspace_id=data["personal_ws_b"].id,
        user_permissions=perms,
        user_id=data["user_b"].id,
    )
    assert res_fail.success is False
    assert "not a family workspace" in res_fail.error
