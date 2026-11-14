"""
Arthsavora Server-Side Authorization & Tenancy Enforcement
Resolves workspace membership, enforces Role-Based Access Control (RBAC),
and activates transaction-local Row-Level Security (RLS) tenant context.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Set
import uuid
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ForbiddenException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import (
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceStatus,
    WorkspaceType,
)
from app.infrastructure.database.rls import set_tenant_context
from app.infrastructure.database.session import get_db_session


class Permission(str, Enum):
    """Centralized, granular permissions across personal, family, and business workspaces."""

    # Workspace Lifecycle & Settings
    VIEW_WORKSPACE = "workspace:view"
    UPDATE_WORKSPACE = "workspace:update"
    ARCHIVE_WORKSPACE = "workspace:archive"
    RESTORE_WORKSPACE = "workspace:restore"
    DELETE_WORKSPACE = "workspace:delete"
    TRANSFER_OWNERSHIP = "workspace:transfer_ownership"

    # Membership & Invitations
    VIEW_MEMBERS = "members:view"
    INVITE_MEMBERS = "members:invite"
    UPDATE_MEMBER_ROLE = "members:update_role"
    REMOVE_MEMBERS = "members:remove"

    # Business Profile
    MANAGE_BUSINESS_PROFILE = "business:manage_profile"

    # Financial Accounts
    VIEW_ACCOUNTS = "accounts:view"
    MANAGE_ACCOUNTS = "accounts:manage"

    # Financial Transactions
    VIEW_TRANSACTIONS = "transactions:view"
    CREATE_TRANSACTIONS = "transactions:create"
    UPDATE_TRANSACTIONS = "transactions:update"
    DELETE_TRANSACTIONS = "transactions:delete"

    # General Ledger & Double-Entry Accounting
    VIEW_LEDGER = "ledger:view"
    MANAGE_LEDGER = "ledger:manage"
    POST_JOURNAL = "ledger:post"
    REVERSE_JOURNAL = "ledger:reverse"
    MANAGE_PERIODS = "ledger:periods"

    # Financial Data Acquisition & Statement Import
    IMPORT_DATA = "data:import"
    VIEW_IMPORTS = "data:view_imports"

    # Transaction Intelligence, Categories & Rules
    VIEW_CATEGORIES = "categories:view"
    MANAGE_CATEGORIES = "categories:manage"
    VIEW_RULES = "rules:view"
    MANAGE_RULES = "rules:manage"
    MANAGE_INTELLIGENCE = "intelligence:manage"

    # Financial Analytics, Insights & Reports
    VIEW_ANALYTICS = "analytics:view"
    EXPORT_ANALYTICS = "analytics:export"

    # Personal Budgeting, Spending Controls & Financial Goals
    VIEW_BUDGETS = "budgets:view"
    MANAGE_BUDGETS = "budgets:manage"
    VIEW_GOALS = "goals:view"
    MANAGE_GOALS = "goals:manage"

    # Recurring Transactions, Subscriptions & Cash-Flow Commitments
    VIEW_RECURRING = "recurring:view"
    MANAGE_RECURRING = "recurring:manage"
    VIEW_SUBSCRIPTIONS = "subscriptions:view"
    MANAGE_SUBSCRIPTIONS = "subscriptions:manage"

    # Financial Forecasting, Cash-Flow Prediction & Scenarios
    VIEW_FORECASTS = "forecasts:view"
    MANAGE_FORECASTS = "forecasts:manage"

    # Financial Anomaly Detection, Fraud Signals & Risk Intelligence
    VIEW_ANOMALIES = "anomalies:view"
    MANAGE_ANOMALIES = "anomalies:manage"

    # AI Financial Assistant & Conversational Intelligence
    USE_ASSISTANT = "assistant:use"
    MANAGE_ASSISTANT = "assistant:manage"

    # Receipt Intelligence, Document Capture & OCR Extraction
    VIEW_DOCUMENTS = "documents:view"
    MANAGE_DOCUMENTS = "documents:manage"


# Explicit Role-to-Permission Mapping Matrix per Workspace Type
ROLE_PERMISSIONS: Dict[str, Dict[str, Set[Permission]]] = {
    # 1. Personal Workspace (Owner-only environment)
    "personal": {
        "owner": set(Permission),
    },
    # 2. Family Workspace (Collaborative household environment with privacy boundaries)
    "family": {
        "owner": set(Permission),
        "admin": {
            Permission.VIEW_WORKSPACE,
            Permission.UPDATE_WORKSPACE,
            Permission.VIEW_MEMBERS,
            Permission.INVITE_MEMBERS,
            Permission.UPDATE_MEMBER_ROLE,
            Permission.REMOVE_MEMBERS,
            Permission.VIEW_ACCOUNTS,
            Permission.MANAGE_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.CREATE_TRANSACTIONS,
            Permission.UPDATE_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.MANAGE_LEDGER,
            Permission.POST_JOURNAL,
            Permission.VIEW_IMPORTS,
            Permission.IMPORT_DATA,
            Permission.VIEW_CATEGORIES,
            Permission.MANAGE_CATEGORIES,
            Permission.VIEW_RULES,
            Permission.MANAGE_RULES,
            Permission.MANAGE_INTELLIGENCE,
            Permission.VIEW_ANALYTICS,
            Permission.EXPORT_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.MANAGE_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.MANAGE_GOALS,
            Permission.VIEW_RECURRING,
            Permission.MANAGE_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.MANAGE_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.MANAGE_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.MANAGE_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.MANAGE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
            Permission.MANAGE_DOCUMENTS,
        },
        "member": {
            Permission.VIEW_WORKSPACE,
            Permission.VIEW_MEMBERS,
            Permission.VIEW_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.CREATE_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.VIEW_IMPORTS,
            Permission.IMPORT_DATA,
            Permission.VIEW_CATEGORIES,
            Permission.VIEW_RULES,
            Permission.VIEW_ANALYTICS,
            Permission.EXPORT_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.MANAGE_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.MANAGE_GOALS,
            Permission.VIEW_RECURRING,
            Permission.MANAGE_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.MANAGE_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.MANAGE_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.MANAGE_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
            Permission.MANAGE_DOCUMENTS,
        },
        "viewer": {
            Permission.VIEW_WORKSPACE,
            Permission.VIEW_MEMBERS,
            Permission.VIEW_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.VIEW_IMPORTS,
            Permission.VIEW_CATEGORIES,
            Permission.VIEW_RULES,
            Permission.VIEW_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.VIEW_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
        },
    },
    # 3. Business Workspace (Commercial environment with accounting & approval roles)
    "business": {
        "owner": set(Permission),
        "admin": {
            Permission.VIEW_WORKSPACE,
            Permission.UPDATE_WORKSPACE,
            Permission.ARCHIVE_WORKSPACE,
            Permission.RESTORE_WORKSPACE,
            Permission.VIEW_MEMBERS,
            Permission.INVITE_MEMBERS,
            Permission.UPDATE_MEMBER_ROLE,
            Permission.REMOVE_MEMBERS,
            Permission.MANAGE_BUSINESS_PROFILE,
            Permission.VIEW_ACCOUNTS,
            Permission.MANAGE_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.CREATE_TRANSACTIONS,
            Permission.UPDATE_TRANSACTIONS,
            Permission.DELETE_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.MANAGE_LEDGER,
            Permission.POST_JOURNAL,
            Permission.REVERSE_JOURNAL,
            Permission.MANAGE_PERIODS,
            Permission.VIEW_IMPORTS,
            Permission.IMPORT_DATA,
            Permission.VIEW_CATEGORIES,
            Permission.MANAGE_CATEGORIES,
            Permission.VIEW_RULES,
            Permission.MANAGE_RULES,
            Permission.MANAGE_INTELLIGENCE,
            Permission.VIEW_ANALYTICS,
            Permission.EXPORT_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.MANAGE_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.MANAGE_GOALS,
            Permission.VIEW_RECURRING,
            Permission.MANAGE_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.MANAGE_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.MANAGE_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.MANAGE_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.MANAGE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
            Permission.MANAGE_DOCUMENTS,
        },
        "accountant": {
            Permission.VIEW_WORKSPACE,
            Permission.VIEW_MEMBERS,
            Permission.MANAGE_BUSINESS_PROFILE,
            Permission.VIEW_ACCOUNTS,
            Permission.MANAGE_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.CREATE_TRANSACTIONS,
            Permission.UPDATE_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.MANAGE_LEDGER,
            Permission.POST_JOURNAL,
            Permission.REVERSE_JOURNAL,
            Permission.MANAGE_PERIODS,
            Permission.VIEW_IMPORTS,
            Permission.IMPORT_DATA,
            Permission.VIEW_CATEGORIES,
            Permission.MANAGE_CATEGORIES,
            Permission.VIEW_RULES,
            Permission.MANAGE_RULES,
            Permission.MANAGE_INTELLIGENCE,
            Permission.VIEW_ANALYTICS,
            Permission.EXPORT_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.MANAGE_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.MANAGE_GOALS,
            Permission.VIEW_RECURRING,
            Permission.MANAGE_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.MANAGE_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.MANAGE_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.MANAGE_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.MANAGE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
            Permission.MANAGE_DOCUMENTS,
        },
        "approver": {
            Permission.VIEW_WORKSPACE,
            Permission.VIEW_MEMBERS,
            Permission.VIEW_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.CREATE_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.POST_JOURNAL,
            Permission.VIEW_IMPORTS,
            Permission.VIEW_CATEGORIES,
            Permission.VIEW_RULES,
            Permission.VIEW_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.VIEW_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.MANAGE_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
            Permission.MANAGE_DOCUMENTS,
        },
        "staff": {
            Permission.VIEW_WORKSPACE,
            Permission.VIEW_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.CREATE_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.VIEW_IMPORTS,
            Permission.IMPORT_DATA,
            Permission.VIEW_CATEGORIES,
            Permission.VIEW_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.VIEW_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
            Permission.MANAGE_DOCUMENTS,
        },
        "viewer": {
            Permission.VIEW_WORKSPACE,
            Permission.VIEW_MEMBERS,
            Permission.VIEW_ACCOUNTS,
            Permission.VIEW_TRANSACTIONS,
            Permission.VIEW_LEDGER,
            Permission.VIEW_IMPORTS,
            Permission.VIEW_CATEGORIES,
            Permission.VIEW_ANALYTICS,
            Permission.VIEW_BUDGETS,
            Permission.VIEW_GOALS,
            Permission.VIEW_RECURRING,
            Permission.VIEW_SUBSCRIPTIONS,
            Permission.VIEW_FORECASTS,
            Permission.VIEW_ANOMALIES,
            Permission.USE_ASSISTANT,
            Permission.VIEW_DOCUMENTS,
        },
    },
}


def has_permission(workspace_type: str, role: str, permission: Permission) -> bool:
    """Evaluates whether a given workspace type and member role possesses the required permission."""
    type_str = str(workspace_type).lower().strip()
    role_str = str(role).lower().strip()
    perms = ROLE_PERMISSIONS.get(type_str, {}).get(role_str, set())
    return permission in perms


@dataclass
class WorkspaceContext:
    """Encapsulates verified tenancy context for the active request."""
    workspace: Workspace
    membership: WorkspaceMember
    current_user: User
    role: WorkspaceRole

    @property
    def workspace_id(self) -> uuid.UUID:
        """Returns the UUID of the active workspace."""
        return self.workspace.id

    @property
    def user(self) -> User:
        """Returns the authenticated User entity."""
        return self.current_user

    def can(self, permission: Permission) -> bool:
        """Helper checking if current context user has the specified permission."""
        role_str = self.role.value if hasattr(self.role, "value") else str(self.role)
        return has_permission(self.workspace.type, role_str, permission)


async def resolve_workspace_id(
    request: Request,
    workspace_id_header: Optional[str] = Header(None, alias="X-Workspace-ID"),
) -> uuid.UUID:
    """Extracts and validates the target workspace ID from path parameters or request header."""
    raw_id = request.path_params.get("workspace_id") or workspace_id_header
    if not raw_id:
        raise ValidationException(
            message="Workspace context is required. Provide 'X-Workspace-ID' header or path parameter.",
            code="MISSING_WORKSPACE_CONTEXT",
        )
    if isinstance(raw_id, uuid.UUID):
        return raw_id
    try:
        return uuid.UUID(str(raw_id))
    except (ValueError, TypeError):
        raise ValidationException(
            message=f"Invalid workspace ID format: '{raw_id}' is not a valid UUID.",
            code="INVALID_WORKSPACE_ID",
        )


async def get_workspace_context_resolver(
    workspace_id: uuid.UUID,
    current_user: User,
    session: AsyncSession,
) -> WorkspaceContext:
    """
    Core resolution logic:
    1. Validates workspace exists and is active.
    2. Validates user has active membership.
    3. Activates PostgreSQL RLS context strictly for this transaction.
    4. Returns safe WorkspaceContext.
    Returns 404 on missing workspace or membership to prevent cross-tenant enumeration.
    """
    # Query workspace
    ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
    ws_result = await session.execute(ws_stmt)
    workspace = ws_result.scalar_one_or_none()

    if not workspace or workspace.status == WorkspaceStatus.DELETED:
        raise NotFoundException(message="Workspace not found.")

    if workspace.status == WorkspaceStatus.SUSPENDED:
        raise ForbiddenException(
            message="Workspace is suspended. All operations and administration are blocked.",
            code="WORKSPACE_SUSPENDED",
        )

    # Query membership
    member_stmt = (
        select(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    member_result = await session.execute(member_stmt)
    membership = member_result.scalar_one_or_none()

    if not membership:
        raise NotFoundException(message="Workspace not found.")

    if membership.status != "active":
        raise ForbiddenException(
            message="Your membership in this workspace is suspended or inactive.",
            code="MEMBERSHIP_INACTIVE",
        )

    # Establish transaction-local PostgreSQL RLS context
    await set_tenant_context(session, workspace_id)

    return WorkspaceContext(
        workspace=workspace,
        membership=membership,
        current_user=current_user,
        role=membership.role,
    )


def require_workspace_roles(allowed_roles: List[WorkspaceRole]) -> Callable:
    """
    Dependency factory that enforces workspace role authorization.
    Rejects unauthorized roles with 403 Forbidden.
    """
    async def role_checker(
        workspace_id: uuid.UUID = Depends(resolve_workspace_id),
        current_user: User = Depends(lambda: None),  # Resolved via wrapper in dependencies
        session: AsyncSession = Depends(get_db_session),
    ) -> WorkspaceContext:
        context = await get_workspace_context_resolver(workspace_id, current_user, session)
        context_role_str = context.role.value if hasattr(context.role, "value") else str(context.role)
        allowed_role_strs = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if context_role_str not in allowed_role_strs:
            raise InsufficientPermissionsException(
                message=f"Action requires one of the following roles: {', '.join(allowed_role_strs)}. Your role is '{context_role_str}'."
            )
        return context

    return role_checker
