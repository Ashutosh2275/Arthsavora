"""
Arthsavora AI Financial Assistant API Endpoints
Authenticated, workspace-scoped RESTful routes and Server-Sent Events (SSE) endpoints
for conversational financial intelligence, tool orchestration, action confirmations, and usage tracking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import uuid
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.core.permissions import Permission, ROLE_PERMISSIONS, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.common import ApiResponse
from app.schemas.assistant_schema import (
    ActionConfirmRequest,
    ActionConfirmResponse,
    AssistantUsageResponse,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.assistant.assistant_service import AssistantService
from app.services.assistant.action_service import AssistantActionService
from app.repositories.assistant_repository import AssistantRepository

router = APIRouter(tags=["AI Financial Assistant & Conversational Intelligence"])


def _extract_user_permissions(context: WorkspaceContext) -> Set[str]:
    """Resolves string representation set of permissions for the active request user."""
    ws_type = context.workspace.type.value if hasattr(context.workspace.type, "value") else str(context.workspace.type)
    role_val = context.role.value if hasattr(context.role, "value") else str(context.role)
    perms = ROLE_PERMISSIONS.get(ws_type, {}).get(role_val, set())
    return {p.value if hasattr(p, "value") else str(p) for p in perms}


# -----------------------------------------------------------------------------
# Conversation Lifecycle Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/conversations",
    response_model=ApiResponse[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create New Financial Conversation",
    description="Initializes a new persistent multi-turn conversational thread for the workspace user.",
)
async def create_conversation(
    payload: Optional[ConversationCreateRequest] = None,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ConversationResponse]:
    service = AssistantService(db)
    title = payload.title if payload else None
    conv = await service.create_conversation(
        workspace_id=context.workspace_id,
        user_id=context.user.id,
        title=title,
    )
    return ApiResponse(
        success=True,
        data=conv,
        message="Financial conversation initialized successfully.",
    )


@router.get(
    "/conversations",
    response_model=ApiResponse[List[ConversationResponse]],
    summary="List Conversations",
    description="Lists active or archived conversation threads for the current user in the workspace.",
)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[ConversationResponse]]:
    service = AssistantService(db)
    convs = await service.list_conversations(
        workspace_id=context.workspace_id,
        user_id=context.user.id,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(
        success=True,
        data=convs,
        message=f"Retrieved {len(convs)} conversations.",
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[ConversationResponse],
    summary="Get Conversation Details",
    description="Retrieves metadata for a specific conversation thread.",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ConversationResponse]:
    service = AssistantService(db)
    conv = await service.get_conversation(
        conversation_id=conversation_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(
        success=True,
        data=conv,
        message="Conversation retrieved successfully.",
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[ConversationResponse],
    summary="Update Conversation",
    description="Updates title or archive status of a conversation thread.",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ConversationResponse]:
    service = AssistantService(db)
    conv = await service.update_conversation(
        conversation_id=conversation_id,
        workspace_id=context.workspace_id,
        title=payload.title,
        status=payload.status,
    )
    return ApiResponse(
        success=True,
        data=conv,
        message="Conversation updated successfully.",
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[bool],
    summary="Delete Conversation",
    description="Soft-deletes a conversation thread and its associated message turns.",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[bool]:
    service = AssistantService(db)
    await service.delete_conversation(
        conversation_id=conversation_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(
        success=True,
        data=True,
        message="Conversation deleted successfully.",
    )


# -----------------------------------------------------------------------------
# Conversation Messages & Turn Dispatch
# -----------------------------------------------------------------------------

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ApiResponse[List[MessageResponse]],
    summary="Get Conversation Messages",
    description="Retrieves chronological message turns with associated tool invocations and action drafts.",
)
async def get_messages(
    conversation_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[MessageResponse]]:
    service = AssistantService(db)
    msgs = await service.get_messages(
        conversation_id=conversation_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(
        success=True,
        data=msgs,
        message=f"Retrieved {len(msgs)} message turns.",
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ApiResponse[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Send Message (Synchronous)",
    description="Submits a financial query, executes needed tools, and returns the synthesized assistant response.",
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[MessageResponse]:
    service = AssistantService(db)
    user_perms = _extract_user_permissions(context)
    resp = await service.send_message(
        conversation_id=conversation_id,
        workspace_id=context.workspace_id,
        user_id=context.user.id,
        user_content=payload.content,
        user_permissions=user_perms,
    )
    return ApiResponse(
        success=True,
        data=resp,
        message="Message processed successfully.",
    )


@router.post(
    "/conversations/{conversation_id}/messages/stream",
    summary="Stream Message Turn (Server-Sent Events)",
    description="Streams real-time token chunks, tool activity indicators, and action drafts via text/event-stream.",
)
async def stream_message(
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    service = AssistantService(db)
    user_perms = _extract_user_permissions(context)

    generator = service.stream_message(
        conversation_id=conversation_id,
        workspace_id=context.workspace_id,
        user_id=context.user.id,
        user_content=payload.content,
        user_permissions=user_perms,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -----------------------------------------------------------------------------
# Controlled Action Draft Confirmation & Cancellation
# -----------------------------------------------------------------------------

@router.post(
    "/actions/{action_id}/confirm",
    response_model=ApiResponse[ActionConfirmResponse],
    summary="Confirm Action Draft",
    description="Explicitly confirms and executes a staged assistant action with permission re-validation.",
)
async def confirm_action(
    action_id: uuid.UUID,
    payload: ActionConfirmRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ActionConfirmResponse]:
    action_service = AssistantActionService(db)
    user_perms = _extract_user_permissions(context)
    result = await action_service.confirm_action(
        draft_id=action_id,
        workspace_id=context.workspace_id,
        user_id=context.user.id,
        confirmation_token=payload.confirmation_token,
        user_permissions=user_perms,
    )
    return ApiResponse(
        success=True,
        data=ActionConfirmResponse(**result),
        message=result["message"],
    )


@router.post(
    "/actions/{action_id}/cancel",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Cancel Action Draft",
    description="Cancels a pending assistant action proposal without executing mutations.",
)
async def cancel_action(
    action_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[Dict[str, Any]]:
    action_service = AssistantActionService(db)
    result = await action_service.cancel_action(
        draft_id=action_id,
        workspace_id=context.workspace_id,
        user_id=context.user.id,
    )
    return ApiResponse(
        success=True,
        data=result,
        message="Action draft cancelled successfully.",
    )


# -----------------------------------------------------------------------------
# Usage & Cost Telemetry
# -----------------------------------------------------------------------------

@router.get(
    "/usage",
    response_model=ApiResponse[AssistantUsageResponse],
    summary="Get Workspace AI Usage Telemetry",
    description="Retrieves aggregate prompt/completion tokens, latency metrics, and estimated costs for the workspace.",
)
async def get_usage_summary(
    since: Optional[datetime] = Query(None, description="Optional ISO datetime cutoff"),
    context: WorkspaceContext = Depends(require_permission(Permission.USE_ASSISTANT)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AssistantUsageResponse]:
    repo = AssistantRepository(db)
    summary = await repo.get_workspace_usage_summary(
        workspace_id=context.workspace_id,
        since_date=since,
    )
    return ApiResponse(
        success=True,
        data=AssistantUsageResponse(**summary),
        message="Usage metrics retrieved successfully.",
    )
