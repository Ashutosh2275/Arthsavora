"""
Arthsavora Workspace Invitation Repository
Data access layer for cryptographically hashed workspace invitations.
Enforces row-level locking for atomic acceptance and prevents duplicate invites.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.workspace import WorkspaceInvitation
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository[WorkspaceInvitation]):
    """Repository handling WorkspaceInvitation persistence and queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, WorkspaceInvitation)

    async def get_by_token_hash(
        self,
        token_hash: str,
        for_update: bool = False,
    ) -> Optional[WorkspaceInvitation]:
        """
        Retrieves invitation by SHA-256 token hash.
        Optionally acquires a row-level lock (FOR UPDATE) to prevent race conditions during acceptance.
        """
        stmt = select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == token_hash)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_and_workspace(
        self,
        invitation_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[WorkspaceInvitation]:
        """Anti-IDOR query ensuring invitation belongs strictly to target workspace."""
        stmt = select(WorkspaceInvitation).where(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_by_email(
        self,
        workspace_id: uuid.UUID,
        email: str,
    ) -> Optional[WorkspaceInvitation]:
        """Checks if a pending, unexpired invitation already exists for this email in this workspace."""
        now = datetime.now(timezone.utc)
        stmt = select(WorkspaceInvitation).where(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.email == email.lower().strip(),
            WorkspaceInvitation.status == "pending",
            WorkspaceInvitation.expires_at > now,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[WorkspaceInvitation]:
        """Lists invitations for a workspace, optionally filtered by status."""
        stmt = select(WorkspaceInvitation).where(
            WorkspaceInvitation.workspace_id == workspace_id
        )
        if status:
            stmt = stmt.where(WorkspaceInvitation.status == status)
        stmt = stmt.order_by(WorkspaceInvitation.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def create(
        self,
        workspace_id: uuid.UUID,
        email: str,
        role: str,
        invited_by_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> WorkspaceInvitation:
        """Schedules creation of a new WorkspaceInvitation record."""
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email.lower().strip(),
            role=role.lower().strip(),
            invited_by_id=invited_by_id,
            token_hash=token_hash,
            status="pending",
            expires_at=expires_at,
        )
        self.session.add(invitation)
        return invitation
