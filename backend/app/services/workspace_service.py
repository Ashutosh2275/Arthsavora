"""
Arthsavora Workspace Application Service
Orchestrates multi-tenant workspaces, business profiles, lifecycle transitions,
centralized permission checks, member role governance, and controlled ownership transfers.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext
from app.domain.events import create_workspace_created_event
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import (
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceStatus,
    WorkspaceType,
)
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import (
    AddMemberRequest,
    OwnershipTransferRequest,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
)


class WorkspaceService:
    """Service orchestrating multi-tenant workspaces, lifecycle, and access governance."""

    @staticmethod
    async def list_user_workspaces(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[Workspace]:
        """Returns all active workspaces the user belongs to."""
        repo = WorkspaceRepository(session)
        return await repo.list_by_user(user_id)

    @staticmethod
    async def create_workspace(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: WorkspaceCreateRequest,
    ) -> Workspace:
        """
        Provisions a new workspace atomically with its owner membership.
        Enforces personal workspace uniqueness, business profile capture, and family boundaries.
        """
        repo = WorkspaceRepository(session)

        # 1. Enforce personal workspace policy: One personal workspace per user
        ws_type_str = data.type.value if hasattr(data.type, "value") else str(data.type)
        if ws_type_str == "personal":
            existing_personal = await repo.get_personal_workspace(user_id)
            if existing_personal:
                raise ConflictException(
                    message="You already have an active personal workspace. Creating multiple personal workspaces is prohibited.",
                    code="DUPLICATE_PERSONAL_WORKSPACE",
                )

        # 2. Build initial settings metadata
        settings_dict = {}
        if ws_type_str == "business" and data.business_profile:
            settings_dict["business_profile"] = data.business_profile.model_dump()
        elif ws_type_str == "family":
            settings_dict["family_settings"] = {
                "sharing_mode": "explicit",
                "shared_account_ids": [],
            }

        # 3. Generate URL-friendly slug
        base_slug = data.name.lower().replace(" ", "-")[:32]
        unique_suffix = uuid.uuid4().hex[:6]
        slug = f"{base_slug}-{unique_suffix}"

        # 4. Provision Workspace entity
        workspace = Workspace(
            name=data.name.strip(),
            slug=slug,
            type=ws_type_str,
            owner_id=user_id,
            default_currency=data.currency.upper().strip(),
            timezone=data.timezone.strip(),
            country=data.country.upper().strip(),
            status=WorkspaceStatus.ACTIVE,
            settings=settings_dict,
        )
        session.add(workspace)
        await session.flush()

        # 5. Add creator as Owner atomically
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role="owner",
            status="active",
        )
        session.add(membership)

        # 6. Audit log & Domain event
        audit = AuditLog(
            workspace_id=workspace.id,
            actor_id=user_id,
            action="workspace:create",
            entity_type="workspace",
            entity_id=workspace.id,
            after_state={
                "name": workspace.name,
                "type": workspace.type,
                "owner_id": str(user_id),
                "default_currency": workspace.default_currency,
                "timezone": workspace.timezone,
            },
        )
        session.add(audit)

        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def get_workspace(
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> Workspace:
        """Retrieves workspace metadata by ID."""
        repo = WorkspaceRepository(session)
        workspace = await repo.get_by_id(workspace_id)
        if not workspace or workspace.status == WorkspaceStatus.DELETED:
            raise NotFoundException(message="Workspace not found.")
        return workspace

    @staticmethod
    async def update_workspace(
        session: AsyncSession,
        context: WorkspaceContext,
        data: WorkspaceUpdateRequest,
    ) -> Workspace:
        """Updates workspace metadata, currency, timezone, and business profile."""
        if not context.can(Permission.UPDATE_WORKSPACE):
            raise InsufficientPermissionsException(message="You do not have permission to update this workspace.")

        workspace = context.workspace
        before_state = {
            "name": workspace.name,
            "timezone": workspace.timezone,
            "currency": workspace.default_currency,
        }

        if data.name is not None:
            clean_name = data.name.strip()
            if not clean_name:
                raise ValidationException(message="Workspace name cannot be empty.", field="name")
            workspace.name = clean_name

        if data.timezone is not None:
            workspace.timezone = data.timezone.strip()

        if data.default_currency is not None:
            workspace.default_currency = data.default_currency.upper().strip()

        if data.country is not None:
            workspace.country = data.country.upper().strip()

        if data.business_profile is not None:
            if not context.can(Permission.MANAGE_BUSINESS_PROFILE):
                raise InsufficientPermissionsException(message="Permission required to manage business profile.")
            existing_settings = dict(workspace.settings or {})
            existing_settings["business_profile"] = data.business_profile.model_dump()
            workspace.settings = existing_settings

        audit = AuditLog(
            workspace_id=workspace.id,
            actor_id=context.current_user.id,
            action="workspace:update",
            entity_type="workspace",
            entity_id=workspace.id,
            before_state=before_state,
            after_state={
                "name": workspace.name,
                "timezone": workspace.timezone,
                "currency": workspace.default_currency,
            },
        )
        session.add(audit)
        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def archive_workspace(
        session: AsyncSession,
        context: WorkspaceContext,
    ) -> Workspace:
        """Transitions active workspace into read-only ARCHIVED state."""
        if not context.can(Permission.ARCHIVE_WORKSPACE):
            raise InsufficientPermissionsException(message="Only workspace owner or admin can archive this workspace.")

        workspace = context.workspace
        if workspace.status != WorkspaceStatus.ACTIVE:
            raise ValidationException(
                message=f"Only ACTIVE workspaces can be archived. Current status is '{workspace.status}'.",
                code="INVALID_STATE_TRANSITION",
            )

        workspace.status = WorkspaceStatus.ARCHIVED

        audit = AuditLog(
            workspace_id=workspace.id,
            actor_id=context.current_user.id,
            action="workspace:archive",
            entity_type="workspace",
            entity_id=workspace.id,
            before_state={"status": WorkspaceStatus.ACTIVE.value},
            after_state={"status": WorkspaceStatus.ARCHIVED.value},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def restore_workspace(
        session: AsyncSession,
        context: WorkspaceContext,
    ) -> Workspace:
        """Restores an ARCHIVED workspace back to ACTIVE status."""
        if not context.can(Permission.RESTORE_WORKSPACE):
            raise InsufficientPermissionsException(message="Only workspace owner or admin can restore this workspace.")

        workspace = context.workspace
        if workspace.status != WorkspaceStatus.ARCHIVED:
            raise ValidationException(
                message=f"Only ARCHIVED workspaces can be restored. Current status is '{workspace.status}'.",
                code="INVALID_STATE_TRANSITION",
            )

        workspace.status = WorkspaceStatus.ACTIVE

        audit = AuditLog(
            workspace_id=workspace.id,
            actor_id=context.current_user.id,
            action="workspace:restore",
            entity_type="workspace",
            entity_id=workspace.id,
            before_state={"status": WorkspaceStatus.ARCHIVED.value},
            after_state={"status": WorkspaceStatus.ACTIVE.value},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def transfer_ownership(
        session: AsyncSession,
        context: WorkspaceContext,
        data: OwnershipTransferRequest,
    ) -> Workspace:
        """
        Executes controlled, atomic ownership transfer:
        1. Verifies caller is current owner.
        2. Verifies explicit confirmation.
        3. Verifies target new owner is an active member.
        4. Swaps roles atomically and audits the transfer.
        """
        if context.role != "owner":
            raise InsufficientPermissionsException(message="Only the current workspace owner can transfer ownership.")

        if not data.confirm:
            raise ValidationException(
                message="Ownership transfer requires explicit confirmation.",
                field="confirm",
            )

        if data.new_owner_id == context.current_user.id:
            raise ValidationException(
                message="Cannot transfer ownership to yourself.",
                field="new_owner_id",
            )

        repo = WorkspaceRepository(session)
        target_membership = await repo.get_member_by_id(context.workspace.id, data.new_owner_id)
        if not target_membership or target_membership.status != "active":
            raise ValidationException(
                message="Target new owner must be an active member of this workspace.",
                field="new_owner_id",
            )

        workspace = context.workspace
        old_owner_id = workspace.owner_id
        new_owner_user_id = target_membership.user_id

        # Update ownership atomically
        workspace.owner_id = new_owner_user_id
        target_membership.role = "owner"
        context.membership.role = data.previous_owner_role.lower().strip() or "admin"

        audit = AuditLog(
            workspace_id=workspace.id,
            actor_id=context.current_user.id,
            action="workspace:transfer_ownership",
            entity_type="workspace",
            entity_id=workspace.id,
            before_state={"owner_id": str(old_owner_id)},
            after_state={
                "owner_id": str(new_owner_user_id),
                "previous_owner_role": context.membership.role,
            },
        )
        session.add(audit)

        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def list_members(
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> List[dict]:
        """Lists active members of a workspace including profile names and emails."""
        repo = WorkspaceRepository(session)
        rows = await repo.list_members_with_user(workspace_id)
        return [
            {
                "id": member.id,
                "workspace_id": member.workspace_id,
                "user_id": member.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "role": member.role,
                "status": member.status,
                "joined_at": member.joined_at,
            }
            for member, user in rows
        ]

    @staticmethod
    async def add_member(
        session: AsyncSession,
        workspace_id: uuid.UUID,
        inviter_id: uuid.UUID,
        data: AddMemberRequest,
    ) -> dict:
        """Invites or attaches an existing registered user to a workspace directly."""
        stmt = select(User).where(User.email == data.email.lower().strip())
        result = await session.execute(stmt)
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise NotFoundException(
                message=f"No user found with email '{data.email}'. The user must register first."
            )

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

        role_str = data.role.value if hasattr(data.role, "value") else str(data.role)
        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user.id,
            role=role_str,
            status="active",
        )
        session.add(membership)

        audit = AuditLog(
            workspace_id=workspace_id,
            actor_id=inviter_id,
            action="member:add",
            entity_type="workspace_member",
            entity_id=membership.id,
            after_state={
                "user_id": str(target_user.id),
                "email": target_user.email,
                "role": role_str,
            },
        )
        session.add(audit)
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

    @staticmethod
    async def update_member_role(
        session: AsyncSession,
        context: WorkspaceContext,
        membership_id: uuid.UUID,
        data: UpdateMemberRoleRequest,
    ) -> dict:
        """Updates a member's role with strict hierarchy validation."""
        if not context.can(Permission.UPDATE_MEMBER_ROLE):
            raise InsufficientPermissionsException(message="Permission required to change member roles.")

        repo = WorkspaceRepository(session)
        target_member = await repo.get_member_by_id(context.workspace.id, membership_id)
        if not target_member or target_member.status != "active":
            raise NotFoundException(message="Active member not found in this workspace.")

        if target_member.role == "owner":
            raise ForbiddenException(message="Cannot alter the role of workspace owner. Use ownership transfer.")

        new_role = data.role.lower().strip()
        if new_role == "owner":
            raise ForbiddenException(message="Cannot assign owner role directly. Use ownership transfer.")

        # Validate allowed roles per workspace type
        allowed_roles_per_type = {
            "personal": {"owner"},
            "family": {"admin", "member", "restricted", "viewer"},
            "business": {"admin", "accountant", "approver", "staff", "viewer"},
        }
        allowed = allowed_roles_per_type.get(context.workspace.type, set())
        if new_role not in allowed:
            raise ValidationException(
                message=f"Role '{new_role}' is not supported in a {context.workspace.type} workspace. Supported: {', '.join(sorted(allowed))}.",
                field="role",
            )

        before_role = target_member.role
        target_member.role = new_role

        audit = AuditLog(
            workspace_id=context.workspace.id,
            actor_id=context.current_user.id,
            action="member:update_role",
            entity_type="workspace_member",
            entity_id=target_member.id,
            before_state={"role": before_role},
            after_state={"role": new_role},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(target_member)

        # Get user details for return
        stmt = select(User).where(User.id == target_member.user_id)
        res = await session.execute(stmt)
        user = res.scalar_one()

        return {
            "id": target_member.id,
            "workspace_id": target_member.workspace_id,
            "user_id": target_member.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": target_member.role,
            "status": target_member.status,
            "joined_at": target_member.joined_at,
        }

    @staticmethod
    async def remove_member(
        session: AsyncSession,
        context: WorkspaceContext,
        membership_id: uuid.UUID,
    ) -> None:
        """
        Revokes a member's access immediately.
        Owners cannot be removed without prior ownership transfer.
        Historical transactions are preserved with actor attribution.
        """
        is_self_removal = (context.membership.id == membership_id)
        if not is_self_removal and not context.can(Permission.REMOVE_MEMBERS):
            raise InsufficientPermissionsException(message="Permission required to remove members.")

        repo = WorkspaceRepository(session)
        target_member = await repo.get_member_by_id(context.workspace.id, membership_id)
        if not target_member or target_member.status != "active":
            raise NotFoundException(message="Active member not found in this workspace.")

        if target_member.role == "owner":
            raise ForbiddenException(
                message="Cannot remove workspace owner. Transfer ownership before leaving or deleting workspace."
            )

        target_member.status = "revoked"
        target_member.revoked_at = datetime.now(timezone.utc)

        audit = AuditLog(
            workspace_id=context.workspace.id,
            actor_id=context.current_user.id,
            action="member:remove",
            entity_type="workspace_member",
            entity_id=target_member.id,
            before_state={"status": "active", "role": target_member.role},
            after_state={"status": "revoked"},
        )
        session.add(audit)
        await session.commit()
