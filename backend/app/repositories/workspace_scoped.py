"""
Arthsavora Workspace-Scoped Repository
Enforces tenant isolation on all queries, bounded pagination, and anti-IDOR checks.
Guarantees that database queries are strictly partitioned by workspace_id.
"""

from typing import List, Optional, Type, TypeVar
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository

T = TypeVar("T")


class WorkspaceScopedRepository(BaseRepository[T]):
    """
    Abstract repository base for all tenant-owned financial entities.
    Requires workspace_id on every retrieval and collection query.
    """

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        super().__init__(session, model_class)

    async def get_by_id_scoped(
        self,
        entity_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[T]:
        """
        Retrieves entity by ID strictly scoped to workspace_id.
        Returns None if entity exists in another workspace (anti-IDOR defense).
        """
        stmt = select(self.model_class).where(
            self.model_class.id == entity_id,
            self.model_class.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_scoped(
        self,
        workspace_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[T]:
        """
        Retrieves a paginated list of entities for a workspace.
        Enforces pagination bounds: limit is capped at 100.
        """
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        stmt = (
            select(self.model_class)
            .where(self.model_class.workspace_id == workspace_id)
            .order_by(self.model_class.created_at.desc())
            .limit(safe_limit)
            .offset(safe_offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_scoped(self, workspace_id: uuid.UUID) -> int:
        """Counts total entities belonging to a workspace."""
        stmt = (
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.workspace_id == workspace_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
