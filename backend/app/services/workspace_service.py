"""
Arthsavora Workspace Application Service
Manages workspace lifecycle, multi-tenant boundaries, and member roles.
"""

from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ConflictException,
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
from app.schemas.workspace import AddMemberRequest, WorkspaceCreateRequest


class WorkspaceService:
    """Service orchestrating multi-tenant workspaces and access membership."""

    @staticmethod
    async def list_user_workspaces(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[Workspace]:
        """Returns all active workspaces the user belongs to."""
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
                Workspace.status == WorkspaceStatus.ACTIVE,
            )
            .order_by(Workspace.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_workspace(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: WorkspaceCreateRequest,
    ) -> Workspace:
        """Provisions a new workspace and registers the creator as OWNER."""
        # Generate URL-friendly slug
        base_slug = data.name.lower().replace(" ", "-")[:32]
        unique_suffix = uuid.uuid4().hex[:6]
        slug = f"{base_slug}-{unique_suffix}"

        workspace = Workspace(
            name=data.name.strip(),
            slug=slug,
            type=data.type,
            owner_id=user_id,
            default_currency=data.currency.upper(),
            timezone=data.timezone,
            status=WorkspaceStatus.ACTIVE,
            settings={},
        )
        session.add(workspace)
        await session.flush()

        # Add creator as Owner
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role=WorkspaceRole.OWNER,
            status="active",
        )
        session.add(membership)
        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def get_workspace(
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> Workspace:
        """Retrieves workspace metadata by ID."""
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        result = await session.execute(stmt)
        workspace = result.scalar_one_or_none()
        if not workspace:
            raise NotFoundException(message="Workspace not found.")
        return workspace

    @staticmethod
    async def list_members(
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> List[dict]:
        """Lists active members of a workspace including profile names and emails."""
        stmt = (
            select(WorkspaceMember, User)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.status == "active",
            )
            .order_by(WorkspaceMember.joined_at.asc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        members = []
        for member, user in rows:
            members.append({
                "id": member.id,
                "workspace_id": member.workspace_id,
                "user_id": member.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "role": member.role,
                "status": member.status,
                "joined_at": member.joined_at,
            })
        return members

    @staticmethod
    async def add_member(
        session: AsyncSession,
        workspace_id: uuid.UUID,
        inviter_id: uuid.UUID,
        data: AddMemberRequest,
    ) -> dict:
        """Invites or attaches an existing user to a workspace."""
        # Find user by email
        stmt = select(User).where(User.email == data.email.lower().strip())
        result = await session.execute(stmt)
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise NotFoundException(
                message=f"No user found with email '{data.email}'. The user must register first."
            )

        # Check existing membership
        existing_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user.id,
        )
        existing_res = await session.execute(existing_stmt)
        existing = existing_res.scalar_one_or_none()

        if existing:
            raise ConflictException(
                message="This user is already a member of the workspace."
            )

        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user.id,
            role=data.role,
            status="active",
        )
        session.add(membership)
        await session.commit()
        await session.refresh(membership)

        return {
            "id": membership.id,
            "workspace_id": membership.workspace_id,
            "user_id": membership.user_id,
            "email": target_user.email,
            "full_name": target_user.full_name,
            "role": membership.role,
            "status": membership.status,
            "joined_at": membership.joined_at,
        }
