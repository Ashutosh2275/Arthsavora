"""
Arthsavora Base Repository Foundation
Generic asynchronous repository providing fundamental persistence operations.
"""

from typing import Generic, Optional, Type, TypeVar
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base generic repository encapsulating SQLAlchemy session and entity mapping."""

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, entity_id: uuid.UUID) -> Optional[T]:
        """Fetches an entity by primary key UUID."""
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def add(self, entity: T) -> T:
        """Schedules a new entity for insertion."""
        self.session.add(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Deletes an entity from persistence."""
        await self.session.delete(entity)

    async def flush(self) -> None:
        """Flushes pending state to the database without committing the transaction."""
        await self.session.flush()

    async def refresh(self, entity: T) -> None:
        """Refreshes entity attributes from the database."""
        await self.session.refresh(entity)
