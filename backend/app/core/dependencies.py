"""
Arthsavora FastAPI Shared Dependencies
Authoritative authentication verification, database session injection,
and workspace tenancy resolution.
"""

from typing import List, Optional
import uuid
from fastapi import Depends, Header, Path
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AccountDeletedException,
    AccountDisabledException,
    UnauthorizedException,
)
from app.core.permissions import (
    WorkspaceContext,
    get_workspace_context_resolver,
    resolve_workspace_id,
)
from app.core.security import decode_token
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import WorkspaceRole
from app.infrastructure.database.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Decodes the incoming Bearer JWT, validates signature and expiration,
    and returns the authoritative User record from PostgreSQL.
    """
    if not token:
        raise UnauthorizedException(
            message="Authentication credentials were not provided.",
            code="AUTHENTICATION_REQUIRED",
        )

    # Independently verify token signature and claims
    payload = decode_token(token, expected_type="access")
    sub = payload.get("sub")
    email = payload.get("email")

    # Look up user by UUID if sub is UUID, or by email
    stmt = select(User).options(selectinload(User.profile))
    try:
        user_uuid = uuid.UUID(str(sub))
        stmt = stmt.where(User.id == user_uuid)
    except (ValueError, TypeError):
        stmt = stmt.where(User.email == (email or str(sub)))

    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(
            message="User account associated with this token does not exist.",
            code="USER_NOT_FOUND",
        )

    # Validate account active state
    if user.is_deleted or user.deleted_at is not None:
        raise AccountDeletedException()

    if not user.is_active:
        raise AccountDisabledException()

    return user


async def get_current_workspace_context(
    workspace_id: uuid.UUID = Depends(resolve_workspace_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceContext:
    """Resolves and validates workspace context and sets transaction-local RLS."""
    return await get_workspace_context_resolver(workspace_id, current_user, session)


def require_role(allowed_roles: List[WorkspaceRole]):
    """Enforces specific workspace roles on route handlers."""
    async def role_dependency(
        context: WorkspaceContext = Depends(get_current_workspace_context),
    ) -> WorkspaceContext:
        context_role_str = context.role.value if hasattr(context.role, "value") else str(context.role)
        allowed_role_strs = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if context_role_str not in allowed_role_strs:
            from app.core.exceptions import InsufficientPermissionsException
            raise InsufficientPermissionsException(
                message=f"Action requires one of: {', '.join(allowed_role_strs)}. Your role is '{context_role_str}'."
            )
        return context

    return role_dependency
