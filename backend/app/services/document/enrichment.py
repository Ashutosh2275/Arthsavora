"""
Arthsavora Document Merchant & Category Enrichment Service
Resolves canonical merchant identities and suggests appropriate financial categories
using Prompt 12 transaction intelligence pipelines and Indian merchant taxonomies.
"""

import logging
import uuid
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.document import StructuredReceiptDataVO
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.merchant import Merchant
from app.repositories.category_repository import CategoryRepository
from app.repositories.merchant_repository import MerchantRepository
from app.services.intelligence.normalizer import DescriptionNormalizer

logger = logging.getLogger(__name__)


class DocumentEnricher:
    """Enriches raw extracted document entities with canonical merchant details and categories."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.merchant_repo = MerchantRepository(session)
        self.category_repo = CategoryRepository(session)

    async def enrich_receipt_data(
        self,
        workspace_id: uuid.UUID,
        receipt: StructuredReceiptDataVO,
    ) -> StructuredReceiptDataVO:
        """
        Enriches merchant name and suggests financial category.
        Never modifies financial totals or ledger entries.
        """
        merchant_candidate = receipt.merchant_name or ""
        if not merchant_candidate:
            return receipt

        # 1. Clean description using deterministic normalizer
        norm_res = DescriptionNormalizer.normalize(merchant_candidate)
        cleaned_name = norm_res.merchant_candidate or norm_res.normalized_description or merchant_candidate

        # 2. Query merchant repository for alias or canonical match
        matched_merchant: Optional[Merchant] = None
        alias_match = await self.merchant_repo.find_alias_match(
            normalized_description=cleaned_name,
            merchant_candidate=cleaned_name,
        )

        if alias_match:
            matched_merchant = alias_match[0]
        else:
            # Substring search in canonical merchants
            merchants = await self.merchant_repo.list_merchants(
                workspace_id=workspace_id,
                search_query=cleaned_name.split()[0] if cleaned_name.split() else cleaned_name,
                limit=5,
            )
            if merchants:
                matched_merchant = merchants[0]

        if matched_merchant:
            receipt.merchant_name = matched_merchant.canonical_name
            if matched_merchant.default_category:
                receipt.suggested_category_id = str(matched_merchant.default_category.id)
                receipt.suggested_category_name = matched_merchant.default_category.name
                return receipt

        # 3. Fallback: Heuristic category matching based on line items or merchant keywords
        if not receipt.suggested_category_id:
            suggested_cat = await self._infer_category_from_keywords(workspace_id, receipt)
            if suggested_cat:
                receipt.suggested_category_id = str(suggested_cat.id)
                receipt.suggested_category_name = suggested_cat.name

        return receipt

    async def _infer_category_from_keywords(
        self,
        workspace_id: uuid.UUID,
        receipt: StructuredReceiptDataVO,
    ) -> Optional[Category]:
        """Infers standard Indian expense category based on receipt content keywords."""
        text_blob = f"{receipt.merchant_name or ''} " + " ".join(
            item.description for item in receipt.line_items
        ).lower()

        target_slug = None
        if any(w in text_blob for w in ["petrol", "diesel", "fuel", "hpcl", "bpcl", "iocl"]):
            target_slug = "transportation-fuel"
        elif any(w in text_blob for w in ["food", "swiggy", "zomato", "restaurant", "cafe", "coffee", "roasters", "paneer", "rice", "naan"]):
            target_slug = "food-dining"
        elif any(w in text_blob for w in ["grocery", "groceries", "supermarket", "atta", "oil", "salt", "fresh", "bazaar"]):
            target_slug = "groceries"
        elif any(w in text_blob for w in ["flight", "hotel", "airline", "indigo", "air india", "travel"]):
            target_slug = "travel"
        elif any(w in text_blob for w in ["croma", "electronics", "laptop", "mobile", "apple", "reliance digital"]):
            target_slug = "electronics-gadgets"

        if target_slug:
            cat = await self.category_repo.get_by_slug(target_slug, workspace_id=workspace_id)
            if cat:
                return cat

        # General default expense category
        categories = await self.category_repo.list_categories(workspace_id=workspace_id, category_type="expense")
        return categories[0] if categories else None
