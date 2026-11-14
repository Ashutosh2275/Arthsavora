"""
Arthsavora Family Finance Management & Collaborative Household Budgeting Domain
Pure domain models, mathematical allocation algorithms, deterministic rounding,
and household settlement tracking with zero-trust privacy boundaries.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID


class FamilyRole(str, Enum):
    """Member roles within a collaborative family workspace."""
    OWNER = "owner"          # Head of household / Workspace creator
    ADMIN = "admin"          # Household administrator (e.g. partner/spouse)
    MEMBER = "member"        # Adult contributing member
    RESTRICTED = "restricted" # Dependent / Teen member with read-only / bounded access
    VIEWER = "viewer"        # Read-only observer


class AllocationMethod(str, Enum):
    """Deterministic algorithms for allocating shared household expenses."""
    EQUAL = "equal"
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    CUSTOM = "custom"


class AllocationStatus(str, Enum):
    """Lifecycle status of an expense allocation."""
    ACTIVE = "active"
    REVISED = "revised"
    CANCELLED = "cancelled"


class SettlementStatus(str, Enum):
    """Settlement status for an individual member's allocated share."""
    PENDING = "pending"
    SETTLED = "settled"
    WAIVED = "waived"


class ContributionType(str, Enum):
    """Types of household pool contributions."""
    MONTHLY = "monthly"
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    ONE_TIME = "one_time"
    VOLUNTARY = "voluntary"


class ContributionStatus(str, Enum):
    """Status of expected or recorded member contributions."""
    EXPECTED = "expected"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    WAIVED = "waived"
    CANCELLED = "cancelled"


class AccountShareScope(str, Enum):
    """Visibility scope when selectively sharing a personal account into family."""
    BALANCE_ONLY = "balance_only"       # Shows aggregate balance only; hides transactions
    SUMMARY_ONLY = "summary_only"       # Shows balance + monthly in/out totals
    FULL_VISIBILITY = "full_visibility" # Shows full account details to family


class FamilyActivityType(str, Enum):
    """Domain events logged to the family workspace activity timeline."""
    MEMBER_INVITED = "member_invited"
    MEMBER_JOINED = "member_joined"
    ROLE_CHANGED = "role_changed"
    MEMBER_REMOVED = "member_removed"
    SHARED_ACCOUNT_ADDED = "shared_account_added"
    SHARED_ACCOUNT_REVOKED = "shared_account_revoked"
    EXPENSE_RECORDED = "expense_recorded"
    EXPENSE_ALLOCATED = "expense_allocated"
    ALLOCATION_REVISED = "allocation_revised"
    CONTRIBUTION_RECORDED = "contribution_recorded"
    CONTRIBUTION_UPDATED = "contribution_updated"
    BUDGET_CREATED = "budget_created"
    BUDGET_UPDATED = "budget_updated"
    GOAL_CREATED = "goal_created"
    GOAL_CONTRIBUTED = "goal_contributed"
    COMMITMENT_ADDED = "commitment_added"
    COMMITMENT_UPDATED = "commitment_updated"
    PRIVACY_UPDATED = "privacy_updated"


@dataclass(frozen=True)
class AllocationItemVO:
    """Immutable allocated share assigned to a family member."""
    member_user_id: UUID
    assigned_share_paise: int
    percentage: Optional[Decimal] = None
    is_paid_by: bool = False
    settlement_status: SettlementStatus = SettlementStatus.PENDING
    notes: Optional[str] = None


@dataclass(frozen=True)
class MemberSettlementVO:
    """Individual member's financial standing within the household."""
    member_user_id: UUID
    full_name: str
    email: str
    role: str
    total_expenses_paid_paise: int
    total_contributions_paid_paise: int
    total_allocated_share_paise: int
    net_position_paise: int  # (expenses_paid + contributions_paid) - allocated_share
    currency: str = "INR"
    status: str = "settled"  # "surplus" (>0), "deficit" (<0), "settled" (==0)


@dataclass(frozen=True)
class SettlementRecommendationVO:
    """Informational netting recommendation (NOT an automated bank transfer)."""
    from_member_id: UUID
    from_member_name: str
    to_member_id: UUID
    to_member_name: str
    amount_paise: int
    currency: str = "INR"
    note: str = "Suggested informational settlement only. Settle externally or record via transfer."


def calculate_equal_allocation(
    total_amount_paise: int,
    member_user_ids: List[UUID],
    payer_user_id: Optional[UUID] = None,
) -> List[AllocationItemVO]:
    """
    Splits an expense amount equally among selected members using integer paise arithmetic.
    Distributes remainder paise deterministically (payer first, then sorted order)
    so that sum(assigned_share_paise) == total_amount_paise exactly.
    """
    if total_amount_paise <= 0:
        raise ValueError("Total expense amount must be greater than zero.")
    if not member_user_ids:
        raise ValueError("At least one member must be selected for expense allocation.")

    # Unique members in deterministic order
    distinct_ids = sorted(list(set(member_user_ids)), key=lambda u: str(u))
    count = len(distinct_ids)

    base_share = total_amount_paise // count
    remainder = total_amount_paise % count

    # Prioritize payer for extra paise if in list, otherwise deterministic order
    sorted_for_remainder = list(distinct_ids)
    if payer_user_id and payer_user_id in sorted_for_remainder:
        sorted_for_remainder.remove(payer_user_id)
        sorted_for_remainder.insert(0, payer_user_id)

    lucky_members: Set[UUID] = set(sorted_for_remainder[:remainder])

    items: List[AllocationItemVO] = []
    for m_id in distinct_ids:
        share = base_share + (1 if m_id in lucky_members else 0)
        pct = (Decimal(share) / Decimal(total_amount_paise) * Decimal(100)).quantize(Decimal("0.01"))
        is_payer = (m_id == payer_user_id)
        items.append(
            AllocationItemVO(
                member_user_id=m_id,
                assigned_share_paise=share,
                percentage=pct,
                is_paid_by=is_payer,
                settlement_status=SettlementStatus.SETTLED if is_payer and share == total_amount_paise else SettlementStatus.PENDING,
            )
        )

    # Invariant assertion
    assert sum(it.assigned_share_paise for it in items) == total_amount_paise
    return items


def calculate_percentage_allocation(
    total_amount_paise: int,
    member_percentages: Dict[UUID, Decimal],
    payer_user_id: Optional[UUID] = None,
) -> List[AllocationItemVO]:
    """
    Allocates an expense according to specified member percentages.
    Enforces percentages sum to 100.00% and resolves fractional paise rounding deterministically.
    """
    if total_amount_paise <= 0:
        raise ValueError("Total expense amount must be greater than zero.")
    if not member_percentages:
        raise ValueError("At least one member percentage must be specified.")

    total_pct = sum(member_percentages.values())
    if abs(total_pct - Decimal("100.00")) > Decimal("0.05"):
        raise ValueError(f"Percentages must sum to 100.00%. Current sum: {total_pct}%")

    raw_shares: Dict[UUID, int] = {}
    remainders: List[Tuple[Decimal, UUID]] = []

    for m_id, pct in member_percentages.items():
        if pct < Decimal("0.00"):
            raise ValueError(f"Member percentage cannot be negative: {pct}%")
        exact_share = (Decimal(total_amount_paise) * pct) / Decimal("100.00")
        int_share = int(exact_share)
        fraction = exact_share - Decimal(int_share)
        raw_shares[m_id] = int_share
        remainders.append((fraction, m_id))

    allocated_so_far = sum(raw_shares.values())
    discrepancy = total_amount_paise - allocated_so_far

    # Distribute discrepancy paise to members with largest fractional parts
    remainders.sort(key=lambda x: (x[0], str(x[1])), reverse=True)
    for i in range(discrepancy):
        m_id = remainders[i % len(remainders)][1]
        raw_shares[m_id] += 1

    items: List[AllocationItemVO] = []
    for m_id, share in raw_shares.items():
        pct = member_percentages[m_id]
        is_payer = (m_id == payer_user_id)
        items.append(
            AllocationItemVO(
                member_user_id=m_id,
                assigned_share_paise=share,
                percentage=pct,
                is_paid_by=is_payer,
                settlement_status=SettlementStatus.SETTLED if is_payer and share == total_amount_paise else SettlementStatus.PENDING,
            )
        )

    # Invariant assertion
    assert sum(it.assigned_share_paise for it in items) == total_amount_paise
    return items


def calculate_fixed_allocation(
    total_amount_paise: int,
    member_shares_paise: Dict[UUID, int],
    payer_user_id: Optional[UUID] = None,
) -> List[AllocationItemVO]:
    """
    Validates and builds fixed amount shares in paise.
    Requires exact sum match against total_amount_paise.
    """
    if total_amount_paise <= 0:
        raise ValueError("Total expense amount must be greater than zero.")
    if not member_shares_paise:
        raise ValueError("At least one member share must be specified.")

    total_shares = sum(member_shares_paise.values())
    if total_shares != total_amount_paise:
        diff = total_amount_paise - total_shares
        raise ValueError(
            f"Sum of fixed member shares ({total_shares} paise) does not match expense total "
            f"({total_amount_paise} paise). Difference: {diff} paise."
        )

    items: List[AllocationItemVO] = []
    for m_id, share in member_shares_paise.items():
        if share < 0:
            raise ValueError(f"Member share cannot be negative: {share} paise.")
        pct = (Decimal(share) / Decimal(total_amount_paise) * Decimal(100)).quantize(Decimal("0.01"))
        is_payer = (m_id == payer_user_id)
        items.append(
            AllocationItemVO(
                member_user_id=m_id,
                assigned_share_paise=share,
                percentage=pct,
                is_paid_by=is_payer,
                settlement_status=SettlementStatus.SETTLED if is_payer and share == total_amount_paise else SettlementStatus.PENDING,
            )
        )

    return items


# Custom allocation behaves identically to fixed allocation: validates explicit shares sum to total
calculate_custom_allocation = calculate_fixed_allocation


def compute_settlement_recommendations(
    member_settlements: List[MemberSettlementVO],
) -> List[SettlementRecommendationVO]:
    """
    Greedy minimum transaction netting algorithm.
    Produces peer-to-peer settlement suggestions based on net positions.
    Debtors pay creditors until all balances net to zero.
    """
    debtors: List[List[Any]] = []   # [member_id, name, remaining_debt_paise]
    creditors: List[List[Any]] = [] # [member_id, name, remaining_credit_paise]

    for ms in member_settlements:
        if ms.net_position_paise < 0:
            debtors.append([ms.member_user_id, ms.full_name, -ms.net_position_paise])
        elif ms.net_position_paise > 0:
            creditors.append([ms.member_user_id, ms.full_name, ms.net_position_paise])

    # Sort largest first for optimal minimal settlements
    debtors.sort(key=lambda x: x[2], reverse=True)
    creditors.sort(key=lambda x: x[2], reverse=True)

    recommendations: List[SettlementRecommendationVO] = []
    d_idx = 0
    c_idx = 0

    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor = debtors[d_idx]
        creditor = creditors[c_idx]

        amount = min(debtor[2], creditor[2])
        if amount > 0:
            recommendations.append(
                SettlementRecommendationVO(
                    from_member_id=debtor[0],
                    from_member_name=debtor[1],
                    to_member_id=creditor[0],
                    to_member_name=creditor[1],
                    amount_paise=amount,
                )
            )
            debtor[2] -= amount
            creditor[2] -= amount

        if debtor[2] == 0:
            d_idx += 1
        if creditor[2] == 0:
            c_idx += 1

    return recommendations


def is_resource_accessible_in_family(
    resource_workspace_id: UUID,
    family_workspace_id: UUID,
    shared_account_ids: Optional[Set[UUID]] = None,
    target_account_id: Optional[UUID] = None,
) -> bool:
    """
    Enforces zero-trust isolation:
    A resource is accessible in a family workspace ONLY IF:
    1. It belongs directly to the family workspace (`resource_workspace_id == family_workspace_id`), OR
    2. It belongs to an account that was explicitly shared with the family workspace.
    Personal resources without explicit sharing are strictly prohibited.
    """
    if resource_workspace_id == family_workspace_id:
        return True
    if target_account_id and shared_account_ids and target_account_id in shared_account_ids:
        return True
    return False
