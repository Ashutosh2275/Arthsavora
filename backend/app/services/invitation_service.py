"""
Arthsavora Workspace Invitation Application Service
Orchestrates cryptographically hashed invitations, token issuance, expiry checks,
row-level locked atomic acceptance, and email binding security.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext
from app.domain.events import create_member_joined_event
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import (
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceRole,
)
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import CreateInvitationRequest


class InvitationService:
    """Service orchestrating secure workspace invitations and token-based acceptance."""

    @staticmethod
    async def create_invitation(
        session: AsyncSession,
        context: WorkspaceContext,
        data: CreateInvitationRequest,
    ) -> Tuple[WorkspaceInvitation, str]:
        """
        Creates a cryptographically secure invitation:
        1. Verifies caller has INVITE_MEMBERS permission.
        2. Validates role compatibility with workspace type.
        3. Prohibits inviting as 'owner' or self-elevation.
        4. Verifies target email is not already an active member.
        5. Generates random 32-byte urlsafe token and stores ONLY its SHA-256 hash.
        6. Returns (invitation, raw_token) so token is returned once to caller.
        """
        if not context.can(Permission.INVITE_MEMBERS):
            raise InsufficientPermissionsException(message="Permission required to invite members.")

        target_role = data.role.lower().strip()
        if target_role == "owner":
            raise ForbiddenException(message="Cannot invite a user as owner. Use ownership transfer.")

        # Check role validity for workspace type
        allowed_roles = {
            "personal": set(),  # Personal workspaces do not permit invites
            "family": {"admin", "member", "restricted", "viewer"},
            "business": {"admin", "accountant", "approver", "staff", "viewer"},
        }
        valid_roles = allowed_roles.get(context.workspace.type, set())
        if target_role not in valid_roles:
            raise ValidationException(
                message=f"Role '{target_role}' cannot be invited into a {context.workspace.type} workspace. Supported roles: {', '.join(sorted(valid_roles))}.",
                field="role",
            )

        clean_email = data.email.lower().strip()

        # Check if user is already an active member
        stmt = (
            select(WorkspaceMember)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(
                WorkspaceMember.workspace_id == context.workspace.id,
                User.email == clean_email,
                WorkspaceMember.status == "active",
            )
        )
        existing_res = await session.execute(stmt)
        if existing_res.scalar_one_or_none():
            raise ConflictException(
                message=f"User with email '{clean_email}' is already an active member of this workspace."
            )

        # Check for active pending invitation
        inv_repo = InvitationRepository(session)
        existing_invite = await inv_repo.get_pending_by_email(context.workspace.id, clean_email)
        if existing_invite:
            raise ConflictException(
                message=f"A pending invitation already exists for '{clean_email}' in this workspace."
            )

        # Generate cryptographically secure random token (32 bytes urlsafe)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Invitation expires in 7 days
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = inv_repo.create(
            workspace_id=context.workspace.id,
            email=clean_email,
            role=target_role,
            invited_by_id=context.current_user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await inv_repo.flush()

        audit = AuditLog(
            workspace_id=context.workspace.id,
            actor_id=context.current_user.id,
            action="invitation:create",
            entity_type="workspace_invitation",
            entity_id=invitation.id,
            after_state={
                "email": clean_email,
                "role": target_role,
                "expires_at": expires_at.isoformat(),
            },
        )
        session.add(audit)
        await session.commit()
        await inv_repo.refresh(invitation)

        return invitation, raw_token

    @staticmethod
    async def list_invitations(
        session: AsyncSession,
        context: WorkspaceContext,
        status: Optional[str] = None,
    ) -> List[WorkspaceInvitation]:
        """Lists invitations for the workspace (returns hash metadata, NEVER raw tokens)."""
        if not context.can(Permission.VIEW_MEMBERS):
            raise InsufficientPermissionsException(message="Permission required to view workspace invitations.")

        inv_repo = InvitationRepository(session)
        return await inv_repo.list_by_workspace(context.workspace.id, status=status)

    @staticmethod
    async def accept_invitation(
        session: AsyncSession,
        raw_token: str,
        accepting_user: User,
    ) -> WorkspaceMember:
        """
        Atomically accepts an invitation:
        1. Computes SHA-256 hash of provided raw token.
        2. Retrieves invitation with row-level lock (FOR UPDATE) to prevent race conditions.
        3. Enforces that invitation is pending, unexpired, and bound to recipient's email.
        4. Grants active membership in the workspace.
        5. Updates invitation to 'accepted'.
        """
        clean_token = raw_token.strip()
        if not clean_token:
            raise ValidationException(message="Invitation token is required.", field="token")

        token_hash = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()

        inv_repo = InvitationRepository(session)
        invitation = await inv_repo.get_by_token_hash(token_hash, for_update=True)

        if not invitation or invitation.status != "pending":
            raise NotFoundException(message="Invalid or already utilized invitation.")

        now = datetime.now(timezone.utc)
        if invitation.expires_at < now:
            invitation.status = "expired"
            await session.commit()
            raise ValidationException(
                message="This workspace invitation has expired. Please request a new invitation.",
                code="INVITATION_EXPIRED",
            )

        # Identity binding enforcement: Accepting user must match invitation email
        if invitation.email.lower() != accepting_user.email.lower():
            raise ForbiddenException(
                message="This invitation was addressed to a different email address.",
                code="INVITATION_RECIPIENT_MISMATCH",
            )

        ws_repo = WorkspaceRepository(session)
        existing_membership = await ws_repo.get_membership(invitation.workspace_id, accepting_user.id)

        if existing_membership:
            existing_membership.role = invitation.role
            existing_membership.status = "active"
            existing_membership.joined_at = now
            existing_membership.revoked_at = None
            membership = existing_membership
        else:
            membership = ws_repo.add_member(
                workspace_id=invitation.workspace_id,
                user_id=accepting_user.id,
                role=invitation.role,
                status="active",
            )

        invitation.status = "accepted"
        invitation.accepted_at = now

        audit = AuditLog(
            workspace_id=invitation.workspace_id,
            actor_id=accepting_user.id,
            action="invitation:accept",
            entity_type="workspace_invitation",
            entity_id=invitation.id,
            after_state={
                "status": "accepted",
                "accepted_by": str(accepting_user.id),
                "role": invitation.role,
            },
        )
        session.add(audit)

        await session.commit()
        await session.refresh(membership)
        return membership

    @staticmethod
    async def revoke_invitation(
        session: AsyncSession,
        context: WorkspaceContext,
        invitation_id: uuid.UUID,
    ) -> WorkspaceInvitation:
        """Revokes a pending workspace invitation."""
        if not context.can(Permission.INVITE_MEMBERS):
            raise InsufficientPermissionsException(message="Permission required to revoke invitations.")

        inv_repo = InvitationRepository(session)
        invitation = await inv_repo.get_by_id_and_workspace(invitation_id, context.workspace.id)
        if not invitation:
            raise NotFoundException(message="Invitation not found in this workspace.")

        if invitation.status != "pending":
            raise ValidationException(
                message=f"Cannot revoke invitation with status '{invitation.status}'.",
                code="INVALID_INVITATION_STATUS",
            )

        invitation.status = "revoked"
        invitation.revoked_at = datetime.now(timezone.utc)

        audit = AuditLog(
            workspace_id=context.workspace.id,
            actor_id=context.current_user.id,
            action="invitation:revoke",
            entity_type="workspace_invitation",
            entity_id=invitation.id,
            before_state={"status": "pending"},
            after_state={"status": "revoked"},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(invitation)
        return invitation
