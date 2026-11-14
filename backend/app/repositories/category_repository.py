"""
Arthsavora Category Repository
Persistence, tree construction, circular hierarchy prevention,
and system category seeding.
"""

import re
from typing import Any, Dict, List, Optional, Set
import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.category_taxonomy import SYSTEM_CATEGORIES, CategoryStatus, CategoryType
from app.domain.exceptions import (
    CategoryInUseError,
    CircularCategoryHierarchyError,
    DomainValidationError,
    SystemCategoryProtectedError,
)
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.transaction import Transaction


class CategoryRepository:
    """Manages transactional category persistence, tree queries, and integrity invariants."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        stmt = (
            select(Category)
            .where(Category.id == category_id)
            .options(selectinload(Category.parent), selectinload(Category.children))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_slug(
        self,
        slug: str,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[Category]:
        """Looks up category by slug within workspace scope or universal system scope."""
        stmt = select(Category).where(Category.slug == slug.lower().strip())
        if workspace_id:
            stmt = stmt.where(
                or_(Category.workspace_id == workspace_id, Category.workspace_id.is_(None))
            ).order_by(Category.workspace_id.desc().nullslast())
        else:
            stmt = stmt.where(Category.workspace_id.is_(None))

        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_categories(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        category_type: Optional[str] = None,
        workspace_type: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[Category]:
        """
        Lists all categories visible to a workspace:
        Both universal system categories (workspace_id IS NULL) and workspace-specific categories.
        """
        stmt = select(Category).options(
            selectinload(Category.parent),
            selectinload(Category.children),
        )

        # Tenancy filter: Global system + workspace custom
        if workspace_id:
            stmt = stmt.where(
                or_(Category.workspace_id == workspace_id, Category.workspace_id.is_(None))
            )
        else:
            stmt = stmt.where(Category.workspace_id.is_(None))

        if not include_archived:
            stmt = stmt.where(Category.status == CategoryStatus.ACTIVE.value)

        if category_type:
            stmt = stmt.where(Category.category_type == category_type)

        if workspace_type and workspace_type != "all":
            stmt = stmt.where(
                or_(Category.workspace_type == "all", Category.workspace_type == workspace_type)
            )

        stmt = stmt.order_by(Category.display_order.asc(), Category.name.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_tree(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        category_type: Optional[str] = None,
        workspace_type: Optional[str] = None,
    ) -> List[Category]:
        """Returns root categories (parent_id IS NULL) with children populated."""
        all_cats = await self.list_categories(
            workspace_id=workspace_id,
            category_type=category_type,
            workspace_type=workspace_type,
            include_archived=False,
        )
        return [c for c in all_cats if c.parent_id is None]

    get_category_tree = get_tree

    async def create_category(
        self,
        name: str,
        category_type: str,
        workspace_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        workspace_type: str = "all",
        transaction_type_compatibility: Optional[List[str]] = None,
        display_order: int = 0,
        is_system: bool = False,
    ) -> Category:
        clean_name = name.strip()
        if not clean_name:
            raise DomainValidationError("Category name cannot be empty.", field="name")

        clean_slug = slug or re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")

        # Parent validation
        if parent_id:
            parent = await self.get_by_id(parent_id)
            if not parent:
                raise DomainValidationError(f"Parent category '{parent_id}' not found.", field="parent_id")
            if parent.status != CategoryStatus.ACTIVE.value:
                raise DomainValidationError("Cannot attach child to an archived parent category.", field="parent_id")

        category = Category(
            workspace_id=workspace_id,
            parent_id=parent_id,
            name=clean_name,
            slug=clean_slug,
            category_type=category_type,
            description=description,
            icon=icon,
            color=color,
            is_system=is_system,
            status=CategoryStatus.ACTIVE.value,
            workspace_type=workspace_type,
            transaction_type_compatibility=transaction_type_compatibility or [],
            display_order=display_order,
        )
        self.session.add(category)
        if parent_id and parent and category not in parent.children:
            parent.children.append(category)
        await self.session.flush()
        return category

    async def update_category(
        self,
        category_id: uuid.UUID,
        name: Optional[str] = None,
        parent_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        status: Optional[str] = None,
        workspace_type: Optional[str] = None,
        display_order: Optional[int] = None,
    ) -> Category:
        cat = await self.get_by_id(category_id)
        if not cat:
            raise DomainValidationError(f"Category '{category_id}' not found.")

        if cat.is_system and name and name != cat.name:
            raise SystemCategoryProtectedError(str(cat.id), cat.name)

        if parent_id is not None:
            if parent_id == cat.id:
                raise CircularCategoryHierarchyError(str(cat.id), str(parent_id))
            # Walk up ancestry tree to prevent circular loops
            await self._validate_no_circular_ancestry(cat.id, parent_id)
            cat.parent_id = parent_id

        if name:
            cat.name = name.strip()
        if description is not None:
            cat.description = description
        if icon is not None:
            cat.icon = icon
        if color is not None:
            cat.color = color
        if status is not None:
            cat.status = status
        if workspace_type is not None:
            cat.workspace_type = workspace_type
        if display_order is not None:
            cat.display_order = display_order

        await self.session.flush()
        return cat

    async def _validate_no_circular_ancestry(self, category_id: uuid.UUID, candidate_parent_id: uuid.UUID) -> None:
        """Walks candidate parent's lineage up to ensure category_id is never an ancestor."""
        visited: Set[uuid.UUID] = {category_id}
        current_id: Optional[uuid.UUID] = candidate_parent_id

        while current_id is not None:
            if current_id in visited:
                raise CircularCategoryHierarchyError(str(category_id), str(candidate_parent_id))
            visited.add(current_id)

            stmt = select(Category.parent_id).where(Category.id == current_id)
            res = await self.session.execute(stmt)
            current_id = res.scalar_one_or_none()

    async def delete_category(self, category_id: uuid.UUID, reassign_to_id: Optional[uuid.UUID] = None) -> None:
        """
        Deletes a category safely.
        If system category, blocks with SystemCategoryProtectedError.
        If referenced by transactions and no reassignment provided, blocks with CategoryInUseError.
        """
        cat = await self.get_by_id(category_id)
        if not cat:
            return

        if cat.is_system:
            raise SystemCategoryProtectedError(str(cat.id), cat.name)

        # Count active transaction references
        stmt = select(func.count()).select_from(Transaction).where(Transaction.category_id == category_id)
        res = await self.session.execute(stmt)
        tx_count = res.scalar_one()

        if tx_count > 0:
            if not reassign_to_id:
                raise CategoryInUseError(str(cat.id), tx_count)
            # Reassign transactions to new category
            reassign_stmt = (
                select(Transaction).where(Transaction.category_id == category_id)
            )
            tx_res = await self.session.execute(reassign_stmt)
            for tx in tx_res.scalars().all():
                tx.category_id = reassign_to_id

        await self.session.delete(cat)
        await self.session.flush()

    async def seed_system_categories(self) -> int:
        """Idempotently seeds universal hierarchical system categories."""
        created_count = 0
        for root_data in SYSTEM_CATEGORIES:
            root_slug = root_data["slug"]
            existing_root = await self.get_by_slug(root_slug, workspace_id=None)

            if not existing_root:
                root_cat = await self.create_category(
                    name=root_data["name"],
                    category_type=root_data["category_type"],
                    workspace_id=None,
                    parent_id=None,
                    slug=root_slug,
                    icon=root_data.get("icon"),
                    color=root_data.get("color"),
                    workspace_type=root_data.get("workspace_type", "all"),
                    display_order=root_data.get("display_order", 0),
                    is_system=True,
                )
                created_count += 1
            else:
                root_cat = existing_root

            # Subcategories
            for sub_data in root_data.get("subcategories", []):
                sub_slug = sub_data["slug"]
                existing_sub = await self.get_by_slug(sub_slug, workspace_id=None)
                if not existing_sub:
                    await self.create_category(
                        name=sub_data["name"],
                        category_type=root_data["category_type"],
                        workspace_id=None,
                        parent_id=root_cat.id,
                        slug=sub_slug,
                        workspace_type=sub_data.get("workspace_type", "all"),
                        display_order=sub_data.get("display_order", 0),
                        is_system=True,
                    )
                    created_count += 1

        return created_count
