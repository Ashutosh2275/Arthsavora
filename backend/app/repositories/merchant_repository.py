"""
Arthsavora Merchant Intelligence Repository
Manages canonical merchants, statement alias dictionaries,
fuzzy/token matching, and system merchant seeding.
"""

from decimal import Decimal
import re
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.category_taxonomy import SYSTEM_MERCHANTS
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.merchant import Merchant, MerchantAlias


class MerchantRepository:
    """Manages recognized merchants and statement alias lookups."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, merchant_id: uuid.UUID) -> Optional[Merchant]:
        stmt = (
            select(Merchant)
            .where(Merchant.id == merchant_id)
            .options(selectinload(Merchant.default_category), selectinload(Merchant.aliases))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_slug(
        self,
        slug: str,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[Merchant]:
        stmt = select(Merchant).where(Merchant.slug == slug.lower().strip())
        if workspace_id:
            stmt = stmt.where(
                or_(Merchant.workspace_id == workspace_id, Merchant.workspace_id.is_(None))
            ).order_by(Merchant.workspace_id.desc().nullslast())
        else:
            stmt = stmt.where(Merchant.workspace_id.is_(None))

        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_merchants(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Merchant]:
        stmt = (
            select(Merchant)
            .options(selectinload(Merchant.default_category), selectinload(Merchant.aliases))
            .where(Merchant.status == "active")
        )

        if workspace_id:
            stmt = stmt.where(
                or_(Merchant.workspace_id == workspace_id, Merchant.workspace_id.is_(None))
            )
        else:
            stmt = stmt.where(Merchant.workspace_id.is_(None))

        if search_query:
            q = f"%{search_query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    Merchant.canonical_name.ilike(q),
                    Merchant.slug.ilike(q),
                    Merchant.merchant_type.ilike(q),
                )
            )

        stmt = stmt.order_by(Merchant.canonical_name.asc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_merchant(
        self,
        canonical_name: str,
        default_category_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        merchant_type: str = "general",
        slug: Optional[str] = None,
        website: Optional[str] = None,
        logo_url: Optional[str] = None,
        is_verified: bool = True,
    ) -> Merchant:
        clean_name = canonical_name.strip()
        clean_slug = slug or re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")

        merchant = Merchant(
            workspace_id=workspace_id,
            canonical_name=clean_name,
            slug=clean_slug,
            default_category_id=default_category_id,
            merchant_type=merchant_type,
            website=website,
            logo_url=logo_url,
            is_verified=is_verified,
            status="active",
        )
        self.session.add(merchant)
        await self.session.flush()
        return merchant

    async def add_alias(
        self,
        merchant_id: uuid.UUID,
        alias: str,
        match_type: str = "exact",
        confidence: Decimal = Decimal("1.0000"),
    ) -> MerchantAlias:
        clean_alias = alias.strip().upper()
        norm_alias = re.sub(r"\s+", " ", clean_alias)

        m_alias = MerchantAlias(
            merchant_id=merchant_id,
            alias=clean_alias,
            normalized_alias=norm_alias,
            match_type=match_type,
            confidence=confidence,
        )
        self.session.add(m_alias)
        await self.session.flush()
        return m_alias

    async def find_alias_match(
        self,
        normalized_description: str,
        merchant_candidate: Optional[str] = None,
    ) -> Optional[Tuple[Merchant, MerchantAlias]]:
        """
        Scans merchant aliases against normalized transaction text.
        Returns the best matching (Merchant, MerchantAlias) pair.
        """
        tokens_to_test = []
        if merchant_candidate:
            tokens_to_test.append(merchant_candidate.strip().upper())
        if normalized_description:
            tokens_to_test.append(normalized_description.strip().upper())

        # 1. Exact match on normalized candidate or description
        for token in tokens_to_test:
            stmt = (
                select(MerchantAlias)
                .options(selectinload(MerchantAlias.merchant).selectinload(Merchant.default_category))
                .where(MerchantAlias.normalized_alias == token)
            )
            res = await self.session.execute(stmt)
            match = res.scalar_one_or_none()
            if match and match.merchant:
                return match.merchant, match

        # 2. Token / Prefix Substring match
        # If any word in the normalized description exactly matches an alias
        desc_words = normalized_description.strip().upper().split()
        if desc_words:
            stmt = (
                select(MerchantAlias)
                .options(selectinload(MerchantAlias.merchant).selectinload(Merchant.default_category))
                .where(MerchantAlias.normalized_alias.in_(desc_words))
                .order_by(MerchantAlias.confidence.desc())
            )
            res = await self.session.execute(stmt)
            match = res.scalars().first()
            if match and match.merchant:
                return match.merchant, match

        # 3. Substring match for multi-word aliases (e.g. "STARBUCKS COFFEE", "TATA 1MG")
        full_text = normalized_description.strip().upper()
        # Query active aliases
        stmt = (
            select(MerchantAlias)
            .options(selectinload(MerchantAlias.merchant).selectinload(Merchant.default_category))
            .where(MerchantAlias.confidence >= Decimal("0.8000"))
        )
        res = await self.session.execute(stmt)
        aliases = list(res.scalars().all())

        for al in aliases:
            if al.normalized_alias in full_text:
                return al.merchant, al

        return None

    async def seed_system_merchants(self) -> int:
        """Seeds canonical Indian merchants and aliases, linking them to default categories."""
        created_count = 0

        # Query all system categories for fast slug lookup
        cat_stmt = select(Category).where(Category.workspace_id.is_(None))
        cat_res = await self.session.execute(cat_stmt)
        cats_by_slug = {c.slug: c.id for c in cat_res.scalars().all()}

        for m_data in SYSTEM_MERCHANTS:
            slug = m_data["slug"]
            existing = await self.get_by_slug(slug, workspace_id=None)

            cat_id = cats_by_slug.get(m_data["default_category_slug"])

            if not existing:
                merchant = await self.create_merchant(
                    canonical_name=m_data["canonical_name"],
                    slug=slug,
                    default_category_id=cat_id,
                    merchant_type=m_data["merchant_type"],
                    workspace_id=None,
                    is_verified=True,
                )
                created_count += 1
            else:
                merchant = existing

            # Seed Aliases
            existing_alias_stmt = select(MerchantAlias.alias).where(MerchantAlias.merchant_id == merchant.id)
            ea_res = await self.session.execute(existing_alias_stmt)
            existing_aliases = set(ea_res.scalars().all())

            for alias_str in m_data.get("aliases", []):
                if alias_str.strip().upper() not in existing_aliases:
                    await self.add_alias(
                        merchant_id=merchant.id,
                        alias=alias_str,
                        confidence=Decimal("1.0000"),
                    )

        return created_count
