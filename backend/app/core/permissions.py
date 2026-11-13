"""
Arthsavora Server-Side Authorization & Tenancy Enforcement
Resolves workspace membership, enforces Role-Based Access Control (RBAC),
and activates transaction-local Row-Level Security (RLS) tenant context.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional
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
)
from app.infrastructure.database.rls import set_tenant_context
from app.infrastructure.database.session import get_db_session


@dataclass
class WorkspaceContext:
    """Encapsulates verified tenancy context for the active request."""
    workspace: Workspace
    membership: WorkspaceMember
    current_user: User
    role: WorkspaceRole


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

    if not workspace or workspace.status != WorkspaceStatus.ACTIVE:
        raise NotFoundException(message="Workspace not found or is currently inactive.")

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
