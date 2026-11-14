"""
Arthsavora AI Financial Assistant Repository
Multi-tenant persistence, workspace-isolated conversation lifecycle,
bounded context window retrieval, action draft state, and usage accounting.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.assistant import (
    AssistantActionDraft,
    AssistantConversation,
    AssistantMessage,
    AssistantUsageLog,
)


class AssistantRepository:
    """Manages transactional persistence for assistant conversations, messages, and action drafts."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # 1. Conversations
    # -------------------------------------------------------------------------

    async def create_conversation(self, conversation: AssistantConversation) -> AssistantConversation:
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[AssistantConversation]:
        stmt = (
            select(AssistantConversation)
            .options(
                selectinload(AssistantConversation.messages),
                selectinload(AssistantConversation.action_drafts),
            )
            .where(
                AssistantConversation.id == conversation_id,
                AssistantConversation.workspace_id == workspace_id,
                AssistantConversation.status != "deleted",
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_conversations(
        self,
        workspace_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AssistantConversation], int]:
        conditions = [
            AssistantConversation.workspace_id == workspace_id,
            AssistantConversation.status != "deleted",
        ]
        if user_id:
            conditions.append(AssistantConversation.user_id == user_id)

        count_stmt = select(func.count(AssistantConversation.id)).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AssistantConversation)
            .where(*conditions)
            .order_by(AssistantConversation.updated_at.desc())
            .limit(min(100, max(1, limit)))
            .offset(max(0, offset))
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def update_conversation(
        self,
        conversation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        title: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[AssistantConversation]:
        conv = await self.get_conversation(conversation_id, workspace_id)
        if not conv:
            return None
        if title is not None:
            conv.title = title
        if status is not None:
            conv.status = status
        await self.session.flush()
        return conv

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """Soft-deletes a conversation thread (preserves financial transactions)."""
        conv = await self.get_conversation(conversation_id, workspace_id)
        if not conv:
            return False
        conv.status = "deleted"
        await self.session.flush()
        return True

    # -------------------------------------------------------------------------
    # 2. Messages
    # -------------------------------------------------------------------------

    async def create_message(self, message: AssistantMessage) -> AssistantMessage:
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_conversation_messages(
        self,
        conversation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> List[AssistantMessage]:
        stmt = (
            select(AssistantMessage)
            .where(
                AssistantMessage.conversation_id == conversation_id,
                AssistantMessage.workspace_id == workspace_id,
            )
            .order_by(AssistantMessage.created_at.asc())
            .limit(min(100, max(1, limit)))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # 3. Action Drafts
    # -------------------------------------------------------------------------

    async def create_action_draft(self, draft: AssistantActionDraft) -> AssistantActionDraft:
        self.session.add(draft)
        await self.session.flush()
        return draft

    async def get_action_draft_by_id(
        self,
        draft_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[AssistantActionDraft]:
        stmt = (
            select(AssistantActionDraft)
            .where(
                AssistantActionDraft.id == draft_id,
                AssistantActionDraft.workspace_id == workspace_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_action_draft_by_token(
        self,
        confirmation_token: str,
        workspace_id: uuid.UUID,
    ) -> Optional[AssistantActionDraft]:
        stmt = (
            select(AssistantActionDraft)
            .where(
                AssistantActionDraft.confirmation_token == confirmation_token,
                AssistantActionDraft.workspace_id == workspace_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # 4. Usage & Cost Logging
    # -------------------------------------------------------------------------

    async def record_usage(self, log: AssistantUsageLog) -> AssistantUsageLog:
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_workspace_usage_summary(
        self,
        workspace_id: uuid.UUID,
        since_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        conditions = [AssistantUsageLog.workspace_id == workspace_id]
        if since_date:
            conditions.append(AssistantUsageLog.created_at >= since_date)

        stmt = (
            select(
                func.count(AssistantUsageLog.id),
                func.coalesce(func.sum(AssistantUsageLog.total_tokens), 0),
                func.coalesce(func.sum(AssistantUsageLog.tokens_prompt), 0),
                func.coalesce(func.sum(AssistantUsageLog.tokens_completion), 0),
                func.coalesce(func.sum(AssistantUsageLog.estimated_cost_usd), Decimal("0.0")),
                func.coalesce(func.avg(AssistantUsageLog.duration_ms), 0),
            )
            .where(*conditions)
        )
        res = await self.session.execute(stmt)
        row = res.one()

        return {
            "total_requests": int(row[0] or 0),
            "total_tokens": int(row[1] or 0),
            "tokens_prompt": int(row[2] or 0),
            "tokens_completion": int(row[3] or 0),
            "estimated_cost_usd": float(row[4] or 0.0),
            "avg_latency_ms": int(round(float(row[5] or 0.0))),
        }
