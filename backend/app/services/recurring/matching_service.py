"""
Arthsavora Transaction Matching & Reconciliation Service
Safely reconciles scheduled occurrences against real posted transactions using
deterministic matching heuristics without modifying general ledger entries or fabricating transactions.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.domain.exceptions import BusinessRuleViolationError
from app.domain.recurring import (
    OccurrenceStatus,
    calculate_transaction_match,
    evaluate_occurrence_state,
)
from app.infrastructure.database.models.recurring import RecurringOccurrence
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.recurring_repository import RecurringRepository
from app.schemas.recurring_schema import OccurrenceResponse


class MatchingService:
    """Orchestrates occurrence-to-transaction reconciliation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringRepository(db)

    async def find_matches_for_occurrence(
        self,
        occurrence_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """
        Scans posted transactions within +/- 10 days of the expected date and computes matching heuristics.
        """
        occ = await self.repo.get_occurrence(occurrence_id, workspace_id)
        if not occ:
            raise NotFoundException(detail=f"Occurrence {occurrence_id} not found")

        min_date = occ.expected_date - timedelta(days=10)
        max_date = occ.expected_date + timedelta(days=10)

        defn = occ.recurring_definition
        direction = defn.direction if defn else "outflow"

        candidates = await self.repo.find_candidate_transactions(
            workspace_id=workspace_id,
            min_date=min_date,
            max_date=max_date,
            direction=direction,
        )

        results: List[Dict[str, Any]] = []

        for tx in candidates:
            match_res = calculate_transaction_match(
                expected_amount_paise=occ.expected_amount_paise,
                tx_amount_paise=tx.amount_paise,
                expected_date=occ.expected_date,
                tx_date=tx.transaction_date,
                expected_merchant_name=defn.merchant_name if defn else None,
                tx_merchant_name=tx.merchant_name,
                expected_description=defn.description if defn else defn.name if defn else None,
                tx_description=tx.description,
                is_variable_amount=defn.is_variable_amount if defn else False,
                direction_match=True,
                account_match=(defn.account_id == tx.account_id) if defn and defn.account_id else False,
            )

            results.append({
                "transaction_id": tx.id,
                "transaction_date": tx.transaction_date,
                "amount_paise": tx.amount_paise,
                "amount": tx.amount,
                "merchant_name": tx.merchant_name,
                "description": tx.description,
                "is_match": match_res.is_match,
                "match_tier": match_res.match_tier,
                "confidence_score": match_res.confidence_score,
                "amount_variance_paise": match_res.amount_variance_paise,
                "date_difference_days": match_res.date_difference_days,
                "reason": match_res.reason,
            })

        # Sort by confidence score descending
        return sorted(results, key=lambda x: x["confidence_score"], reverse=True)

    async def match_occurrence_to_transaction(
        self,
        occurrence_id: uuid.UUID,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> OccurrenceResponse:
        """
        Associates an expected occurrence with an actual posted transaction.
        Enforces workspace boundary and ensures transaction exists.
        """
        occ = await self.repo.get_occurrence(occurrence_id, workspace_id)
        if not occ:
            raise NotFoundException(detail=f"Occurrence {occurrence_id} not found")

        # Fetch transaction
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.workspace_id == workspace_id,
            Transaction.is_deleted.is_(False),
        )
        tx = (await self.db.execute(stmt)).scalar_one_or_none()
        if not tx:
            raise NotFoundException(detail=f"Transaction {transaction_id} not found in workspace")

        defn = occ.recurring_definition
        match_res = calculate_transaction_match(
            expected_amount_paise=occ.expected_amount_paise,
            tx_amount_paise=tx.amount_paise,
            expected_date=occ.expected_date,
            tx_date=tx.transaction_date,
            expected_merchant_name=defn.merchant_name if defn else None,
            tx_merchant_name=tx.merchant_name,
            expected_description=defn.description if defn else defn.name if defn else None,
            tx_description=tx.description,
            is_variable_amount=defn.is_variable_amount if defn else False,
        )

        occ.matched_transaction_id = tx.id
        occ.matched_amount_paise = tx.amount_paise
        occ.amount_variance_paise = match_res.amount_variance_paise
        occ.match_confidence = match_res.confidence_score
        occ.status = OccurrenceStatus.MATCHED.value
        if notes:
            occ.notes = notes

        updated = await self.repo.update_occurrence(occ)

        return OccurrenceResponse(
            id=updated.id,
            workspace_id=updated.workspace_id,
            recurring_definition_id=updated.recurring_definition_id,
            recurring_name=defn.name if defn else None,
            direction=defn.direction if defn else None,
            expected_date=updated.expected_date,
            expected_amount_paise=updated.expected_amount_paise,
            expected_amount=updated.expected_amount,
            currency=updated.currency,
            status=updated.status,
            matched_transaction_id=updated.matched_transaction_id,
            matched_amount_paise=updated.matched_amount_paise,
            matched_amount=Decimal(updated.matched_amount_paise) / Decimal("100.0000") if updated.matched_amount_paise else None,
            amount_variance_paise=updated.amount_variance_paise,
            match_confidence=updated.match_confidence,
            notes=updated.notes,
            generated_at=updated.generated_at,
            confirmed_at=updated.confirmed_at,
            updated_at=updated.updated_at,
        )

    async def unmatch_occurrence(
        self,
        occurrence_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> OccurrenceResponse:
        """Removes transaction association and resets occurrence status based on date."""
        occ = await self.repo.get_occurrence(occurrence_id, workspace_id)
        if not occ:
            raise NotFoundException(detail=f"Occurrence {occurrence_id} not found")

        occ.matched_transaction_id = None
        occ.matched_amount_paise = None
        occ.amount_variance_paise = None
        occ.match_confidence = None

        new_status = evaluate_occurrence_state(
            expected_date=occ.expected_date,
            current_date=date.today(),
            matched_transaction_id=None,
        )
        occ.status = new_status.value

        updated = await self.repo.update_occurrence(occ)
        defn = occ.recurring_definition

        return OccurrenceResponse(
            id=updated.id,
            workspace_id=updated.workspace_id,
            recurring_definition_id=updated.recurring_definition_id,
            recurring_name=defn.name if defn else None,
            direction=defn.direction if defn else None,
            expected_date=updated.expected_date,
            expected_amount_paise=updated.expected_amount_paise,
            expected_amount=updated.expected_amount,
            currency=updated.currency,
            status=updated.status,
            matched_transaction_id=None,
            matched_amount_paise=None,
            matched_amount=None,
            amount_variance_paise=None,
            match_confidence=None,
            notes=updated.notes,
            generated_at=updated.generated_at,
            confirmed_at=updated.confirmed_at,
            updated_at=updated.updated_at,
        )
