"""
Arthsavora Workspace Repository
Data access layer for workspaces, multi-tenant boundaries, and member records.
"""

from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models import User, Workspace, WorkspaceMember, WorkspaceStatus
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository handling Workspace and WorkspaceMember persistence operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Workspace)

    async def get_by_slug(self, slug: str) -> Optional[Workspace]:
        """Looks up a workspace by its unique URL slug."""
        stmt = select(Workspace).where(Workspace.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> List[Workspace]:
        """Retrieves all active workspaces accessible to the user."""
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
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_membership(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[WorkspaceMember]:
        """Retrieves user membership within a specific workspace."""
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_members_with_user(
        self,
        workspace_id: uuid.UUID,
    ) -> List[Tuple[WorkspaceMember, User]]:
        """Retrieves active workspace members joined with User profiles."""
        stmt = (
            select(WorkspaceMember, User)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.status == "active",
            )
            .order_by(WorkspaceMember.joined_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    def add_member(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        status: str = "active",
    ) -> WorkspaceMember:
        """Schedules a new WorkspaceMember record."""
        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            status=status,
        )
        self.session.add(membership)
        return membership

    async def get_personal_workspace(self, user_id: uuid.UUID) -> Optional[Workspace]:
        """Looks up an active personal workspace owned by the user."""
        stmt = select(Workspace).where(
            Workspace.owner_id == user_id,
            Workspace.type == "personal",
            Workspace.status != WorkspaceStatus.DELETED,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_member_by_id(
        self,
        workspace_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> Optional[WorkspaceMember]:
        """Looks up membership record by ID scoped to target workspace."""
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.id == membership_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active_owners(self, workspace_id: uuid.UUID) -> int:
        """Counts active members holding the OWNER role."""
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == "owner",
                WorkspaceMember.status == "active",
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
