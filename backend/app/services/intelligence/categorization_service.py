"""
Arthsavora Transaction Categorization Service
Hybrid classification pipeline orchestrating description normalization,
deterministic rule engine, merchant alias resolution, ML prediction fallback,
confidence scoring, and transparent explainability.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.domain.category_taxonomy import ClassificationMethod, ConfidenceBand
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.category_repository import CategoryRepository
from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.merchant_repository import MerchantRepository
from app.repositories.rule_repository import RuleRepository
from app.services.intelligence.ml_classifier import ml_classifier
from app.services.intelligence.normalizer import DescriptionNormalizer
from app.services.intelligence.rule_engine import RuleEngine


class CategorizationService:
    """
    Core application service powering transaction intelligence.
    Enforces the hybrid decision sequence without code execution or silent accounting corruption.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.category_repo = CategoryRepository(session)
        self.merchant_repo = MerchantRepository(session)
        self.rule_repo = RuleRepository(session)
        self.intel_repo = IntelligenceRepository(session)

    async def seed_system_defaults(self) -> Dict[str, int]:
        """Seeds initial system categories and merchants with Indian aliases."""
        cat_count = await self.category_repo.seed_system_categories()
        merch_count = await self.merchant_repo.seed_system_merchants()
        return {"categories": cat_count, "merchants": merch_count}

    async def categorize_workspace_transactions(
        self,
        workspace_id: uuid.UUID,
        transaction_ids: Optional[List[uuid.UUID]] = None,
        actor_id: Optional[uuid.UUID] = None,
        force_reclassify: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid categorization for a batch of transactions in a workspace.
        """
        if not transaction_ids:
            stmt = select(Transaction.id).where(
                Transaction.workspace_id == workspace_id,
                Transaction.category_id.is_(None),
            )
            res = await self.session.execute(stmt)
            transaction_ids = list(res.scalars().all())

        results = []
        for tx_id in transaction_ids:
            res = await self.categorize_transaction(
                workspace_id=workspace_id,
                transaction_id=tx_id,
                actor_id=actor_id,
                force_reclassify=force_reclassify,
            )
            results.append(res)
        return results

    async def categorize_transaction(
        self,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        force_reclassify: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes the hybrid decision process on a transaction:
        1. Tenant validation & eligibility check.
        2. Normalizes description and updates transaction normalized text.
        3. Checks deterministic user-defined & system rules.
        4. Resolves verified merchant aliases.
        5. Executes ML classification pipeline fallback.
        6. Persists explainable suggestion.
        """
        # 1. Fetch transaction with tenant verification
        stmt = (
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.workspace_id == workspace_id,
            )
            .options(
                selectinload(Transaction.account),
                selectinload(Transaction.category),
            )
        )
        res = await self.session.execute(stmt)
        tx = res.scalar_one_or_none()

        if not tx:
            raise NotFoundException(f"Transaction '{transaction_id}' not found in workspace.")

        # If already classified and confirmed by user, and not force reclassifying
        if tx.category_id and not tx.is_ai_predicted and not force_reclassify:
            existing_cl = await self.intel_repo.get_classification_by_transaction_id(workspace_id, transaction_id)
            if existing_cl:
                return self._format_classification_result(existing_cl, tx)

        # 2. Normalize Description
        norm_res = DescriptionNormalizer.normalize(tx.description)
        tx.normalized_description = norm_res.normalized_description
        if not tx.merchant_name and norm_res.merchant_candidate:
            tx.merchant_name = norm_res.merchant_candidate

        # 3. Rule-Based Classification (Priority 1)
        account_type = tx.account.account_type if tx.account else None
        active_rules = await self.rule_repo.list_rules(workspace_id, include_disabled=False)

        rule_match = RuleEngine.evaluate(
            rules=active_rules,
            normalized_description=norm_res.normalized_description,
            merchant_name=tx.merchant_name,
            direction=tx.direction,
            amount_paise=tx.amount_paise,
            transaction_type=tx.transaction_type,
            account_type=account_type,
        )

        if rule_match:
            method = (
                ClassificationMethod.USER_RULE.value
                if rule_match.rule_scope in ("workspace", "user")
                else ClassificationMethod.SYSTEM_RULE.value
            )
            cl = await self.intel_repo.create_classification(
                workspace_id=workspace_id,
                transaction_id=tx.id,
                suggested_category_id=rule_match.suggested_category_id,
                suggested_merchant_id=rule_match.suggested_merchant_id,
                suggested_merchant_name=rule_match.suggested_merchant_name or tx.merchant_name,
                confidence_score=Decimal("1.0000"),
                confidence_band=ConfidenceBand.HIGH.value,
                method=method,
                rule_id=rule_match.rule_id,
                model_version="v1.0.0",
                explanation=rule_match.explanation,
                status="suggested",
            )
            return self._format_classification_result(cl, tx)

        # 4. Merchant Alias Resolution (Priority 2)
        merchant_match = await self.merchant_repo.find_alias_match(
            normalized_description=norm_res.normalized_description,
            merchant_candidate=tx.merchant_name,
        )

        if merchant_match:
            merchant, alias = merchant_match
            # Look up merchant's default category
            default_cat = merchant.default_category
            if not default_cat and merchant.default_category_id:
                default_cat = await self.category_repo.get_by_id(merchant.default_category_id)

            if default_cat:
                explanation = f"Matched verified merchant alias '{alias.alias}' ({merchant.canonical_name})"
                cl = await self.intel_repo.create_classification(
                    workspace_id=workspace_id,
                    transaction_id=tx.id,
                    suggested_category_id=default_cat.id,
                    suggested_merchant_id=merchant.id,
                    suggested_merchant_name=merchant.canonical_name,
                    confidence_score=Decimal(str(alias.confidence)),
                    confidence_band=ConfidenceBand.HIGH.value,
                    method=ClassificationMethod.MERCHANT_ALIAS.value,
                    model_version="v1.0.0",
                    explanation=explanation,
                    status="suggested",
                )
                return self._format_classification_result(cl, tx)

        # 5. Machine-Learning Prediction (Priority 3)
        ml_pred = ml_classifier.predict(norm_res.normalized_description)
        cat_slug = ml_pred.predicted_category_slug

        # Look up category by slug
        pred_cat = await self.category_repo.get_by_slug(cat_slug, workspace_id=workspace_id)
        if not pred_cat:
            # Fallback to general expense or income
            fallback_slug = "other-income" if tx.direction == "inflow" else "general-shopping"
            pred_cat = await self.category_repo.get_by_slug(fallback_slug, workspace_id=workspace_id)

        cat_id = pred_cat.id if pred_cat else tx.category_id

        if not cat_id:
            # If no category exists at all, get first available category
            all_cats = await self.category_repo.list_categories(workspace_id=workspace_id)
            if all_cats:
                cat_id = all_cats[0].id
            else:
                # Seed system categories if none exist
                await self.category_repo.seed_system_categories()
                all_cats = await self.category_repo.list_categories(workspace_id=workspace_id)
                cat_id = all_cats[0].id

        cl = await self.intel_repo.create_classification(
            workspace_id=workspace_id,
            transaction_id=tx.id,
            suggested_category_id=cat_id,
            suggested_merchant_name=tx.merchant_name,
            confidence_score=Decimal(str(ml_pred.confidence_score)),
            confidence_band=ml_pred.confidence_band,
            method=ClassificationMethod.ML_MODEL.value,
            model_version=ml_pred.model_version,
            explanation=ml_pred.explanation,
            status="suggested",
        )

        return self._format_classification_result(cl, tx)

    async def preview_suggestion(
        self,
        description: str,
        workspace_id: Optional[uuid.UUID] = None,
        direction: str = "outflow",
        amount_paise: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Lightweight preview endpoint evaluating description without persisting to DB.
        Useful for live form input categorization.
        """
        norm_res = DescriptionNormalizer.normalize(description)

        # 1. Rules
        if workspace_id:
            active_rules = await self.rule_repo.list_rules(workspace_id, include_disabled=False)
            rule_match = RuleEngine.evaluate(
                rules=active_rules,
                normalized_description=norm_res.normalized_description,
                merchant_name=norm_res.merchant_candidate,
                direction=direction,
                amount_paise=amount_paise,
            )
            if rule_match:
                cat = await self.category_repo.get_by_id(rule_match.suggested_category_id)
                return {
                    "normalized_description": norm_res.normalized_description,
                    "merchant_candidate": norm_res.merchant_candidate,
                    "payment_channel": norm_res.payment_channel,
                    "suggested_category_id": str(rule_match.suggested_category_id),
                    "suggested_category_name": cat.name if cat else "Categorized",
                    "confidence_score": 1.0,
                    "confidence_band": ConfidenceBand.HIGH.value,
                    "method": ClassificationMethod.USER_RULE.value,
                    "explanation": rule_match.explanation,
                }

        # 2. Merchant Aliases
        merchant_match = await self.merchant_repo.find_alias_match(
            normalized_description=norm_res.normalized_description,
            merchant_candidate=norm_res.merchant_candidate,
        )
        if merchant_match:
            merchant, alias = merchant_match
            cat = merchant.default_category
            if not cat and merchant.default_category_id:
                cat = await self.category_repo.get_by_id(merchant.default_category_id)

            return {
                "normalized_description": norm_res.normalized_description,
                "merchant_candidate": merchant.canonical_name,
                "payment_channel": norm_res.payment_channel,
                "suggested_category_id": str(cat.id) if cat else None,
                "suggested_category_name": cat.name if cat else "Uncategorized",
                "confidence_score": float(alias.confidence),
                "confidence_band": ConfidenceBand.HIGH.value,
                "method": ClassificationMethod.MERCHANT_ALIAS.value,
                "explanation": f"Matched verified merchant '{merchant.canonical_name}'",
            }

        # 3. ML Model
        ml_res = ml_classifier.predict(norm_res.normalized_description)
        cat = await self.category_repo.get_by_slug(ml_res.predicted_category_slug, workspace_id=workspace_id)

        return {
            "normalized_description": norm_res.normalized_description,
            "merchant_candidate": norm_res.merchant_candidate,
            "payment_channel": norm_res.payment_channel,
            "suggested_category_id": str(cat.id) if cat else None,
            "suggested_category_name": cat.name if cat else ml_res.predicted_category_slug.replace("-", " ").title(),
            "confidence_score": ml_res.confidence_score,
            "confidence_band": ml_res.confidence_band,
            "method": ClassificationMethod.ML_MODEL.value,
            "explanation": ml_res.explanation,
        }

    def _format_classification_result(self, cl: Any, tx: Transaction) -> Dict[str, Any]:
        cat_name = cl.suggested_category.name if hasattr(cl, "suggested_category") and cl.suggested_category else "Uncategorized"
        return {
            "classification_id": str(cl.id),
            "workspace_id": str(cl.workspace_id),
            "transaction_id": str(cl.transaction_id),
            "original_description": tx.description,
            "normalized_description": tx.normalized_description,
            "merchant_name": tx.merchant_name or cl.suggested_merchant_name,
            "suggested_category_id": str(cl.suggested_category_id),
            "suggested_category_name": cat_name,
            "confidence_score": float(cl.confidence_score),
            "confidence_band": cl.confidence_band,
            "method": cl.method,
            "model_version": cl.model_version,
            "explanation": cl.explanation,
            "status": cl.status,
            "created_at": cl.created_at.isoformat() if hasattr(cl, "created_at") and cl.created_at else None,
        }
