"""
Arthsavora Receipt-to-Transaction Matcher Service
Correlates extracted receipt financial data with existing transactions in the workspace
to provide exact and candidate match recommendations with transparent evidence scoring.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.document import StructuredReceiptDataVO, TransactionMatchStatus, parse_indian_date
from app.infrastructure.database.models.transaction import Transaction

logger = logging.getLogger(__name__)


@dataclass
class TransactionMatchCandidate:
    transaction_id: uuid.UUID
    match_status: TransactionMatchStatus
    match_score: Decimal
    evidence: Dict[str, Any]
    transaction_summary: Dict[str, Any]


class TransactionMatcher:
    """Matches extracted receipt details against existing workspace transactions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_matches(
        self,
        workspace_id: uuid.UUID,
        receipt: StructuredReceiptDataVO,
        date_window_days: int = 5,
    ) -> List[TransactionMatchCandidate]:
        """
        Searches workspace transactions for matches against receipt total amount and date.
        """
        if receipt.total_amount_paise <= 0:
            return []

        # Parse date
        receipt_date: Optional[date] = None
        if receipt.receipt_date:
            receipt_date = parse_indian_date(receipt.receipt_date)

        # Base query: matching workspace and non-deleted transactions
        stmt = (
            select(Transaction)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.deleted_at.is_(None),
            )
        )

        # Date window filter if receipt date is available
        if receipt_date:
            start_date = receipt_date - timedelta(days=date_window_days)
            end_date = receipt_date + timedelta(days=date_window_days)
            stmt = stmt.where(
                and_(
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                )
            )

        res = await self.session.execute(stmt)
        transactions = list(res.scalars().all())

        candidates: List[TransactionMatchCandidate] = []

        merchant_norm = (receipt.merchant_name or "").lower().strip()

        for tx in transactions:
            score = Decimal("0.0")
            evidence: Dict[str, Any] = {}

            # 1. Amount Comparison (Weight: 50%)
            if tx.amount_paise == receipt.total_amount_paise:
                score += Decimal("0.50")
                evidence["amount_match"] = "exact"
            elif abs(tx.amount_paise - receipt.total_amount_paise) <= 100:  # <= ₹1 rounding difference
                score += Decimal("0.45")
                evidence["amount_match"] = "within_1_inr"
            else:
                continue  # Amount does not match; skip

            # 2. Date Comparison (Weight: 30%)
            if receipt_date:
                day_diff = abs((tx.transaction_date - receipt_date).days)
                if day_diff == 0:
                    score += Decimal("0.30")
                    evidence["date_match"] = "same_day"
                elif day_diff <= 1:
                    score += Decimal("0.25")
                    evidence["date_match"] = f"{day_diff}_day_diff"
                elif day_diff <= 3:
                    score += Decimal("0.18")
                    evidence["date_match"] = f"{day_diff}_days_diff"
                else:
                    score += Decimal("0.10")
                    evidence["date_match"] = f"{day_diff}_days_diff"

            # 3. Merchant / Description Comparison (Weight: 20%)
            tx_desc = (tx.description or "").lower()
            if merchant_norm and (merchant_norm in tx_desc or any(token in tx_desc for token in merchant_norm.split() if len(token) > 3)):
                score += Decimal("0.20")
                evidence["merchant_match"] = True
            else:
                evidence["merchant_match"] = False

            # Assign Status
            if score >= Decimal("0.90"):
                match_status = TransactionMatchStatus.EXACT
            elif score >= Decimal("0.65"):
                match_status = TransactionMatchStatus.CANDIDATE
            else:
                match_status = TransactionMatchStatus.NONE

            candidates.append(
                TransactionMatchCandidate(
                    transaction_id=tx.id,
                    match_status=match_status,
                    match_score=score,
                    evidence=evidence,
                    transaction_summary={
                        "id": str(tx.id),
                        "transaction_date": tx.transaction_date.isoformat(),
                        "amount": str(tx.amount),
                        "amount_paise": tx.amount_paise,
                        "description": tx.description,
                        "direction": tx.direction,
                    },
                )
            )

        # Sort by match score descending
        candidates.sort(key=lambda c: c.match_score, reverse=True)

        # Flag ambiguous if multiple candidates share the top score >= 0.85
        if len(candidates) > 1 and candidates[0].match_score >= Decimal("0.85") and candidates[1].match_score == candidates[0].match_score:
            candidates[0].match_status = TransactionMatchStatus.AMBIGUOUS
            candidates[1].match_status = TransactionMatchStatus.AMBIGUOUS

        return candidates
