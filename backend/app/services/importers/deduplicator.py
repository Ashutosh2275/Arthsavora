"""
Arthsavora Statement Deduplicator Engine
Multi-level duplicate detection: Exact matching, Probable matching, and Intra-batch duplicates.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.import_types import DuplicateStatus
from app.infrastructure.database.models.transaction import Transaction


class StatementDeduplicator:
    """Detects exact and probable transaction duplicates against existing ledger data."""

    @classmethod
    async def deduplicate_batch(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        account_id: Optional[uuid.UUID],
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Runs multi-level deduplication across candidate rows:
        1. Checks intra-batch duplicates.
        2. Queries workspace transactions in the matching date/amount envelope.
        3. Identifies exact and probable matches.
        """
        if not candidates:
            return candidates

        # 1. Fetch relevant existing transactions for workspace / account
        # Collect date range and amount ranges
        dates = [c["normalized"]["transaction_date"] for c in candidates if c["normalized"].get("transaction_date")]
        if not dates:
            return candidates

        min_date_str = min(dates)
        max_date_str = max(dates)
        try:
            start_dt = datetime.strptime(min_date_str, "%Y-%m-%d") - timedelta(days=2)
            end_dt = datetime.strptime(max_date_str, "%Y-%m-%d") + timedelta(days=2)
        except Exception:
            start_dt = datetime.now() - timedelta(days=90)
            end_dt = datetime.now() + timedelta(days=1)

        stmt = select(Transaction).where(
            Transaction.workspace_id == workspace_id,
            Transaction.transaction_date >= start_dt,
            Transaction.transaction_date <= end_dt,
            Transaction.status.in_(["posted", "pending"]),
        )
        if account_id:
            stmt = stmt.where(Transaction.account_id == account_id)

        res = await session.execute(stmt)
        existing_txs = list(res.scalars().all())

        # Build fast lookup indexes
        # By external_id / external_reference
        by_ref: Dict[str, Transaction] = {}
        # By (date_str, amount_paise, direction)
        by_triple: Dict[str, List[Transaction]] = {}

        for tx in existing_txs:
            ext_id = getattr(tx, "external_transaction_id", None) or getattr(tx, "source_reference", None)
            if ext_id:
                by_ref[str(ext_id).strip().upper()] = tx
            
            d_str = tx.transaction_date.strftime("%Y-%m-%d") if tx.transaction_date else ""
            key = f"{d_str}:{tx.amount_paise}:{tx.direction}"
            if key not in by_triple:
                by_triple[key] = []
            by_triple[key].append(tx)

        # 2. Track intra-batch signatures to prevent internal duplicates
        seen_batch_signatures: Dict[str, int] = {}

        # 3. Evaluate each candidate
        for item in candidates:
            norm = item["normalized"]
            c_date = norm.get("transaction_date")
            c_paise = norm.get("amount_paise")
            c_dir = norm.get("direction")
            c_ref = (norm.get("reference_number") or "").strip().upper()
            c_desc = (norm.get("description") or "").strip().upper()

            # Default
            dup_status = DuplicateStatus.NONE.value
            dup_match_id: Optional[uuid.UUID] = None
            dup_reason: Optional[str] = None

            # Check Intra-batch duplicate
            batch_sig = f"{c_date}:{c_paise}:{c_dir}:{c_ref or c_desc[:20]}"
            if batch_sig in seen_batch_signatures:
                prev_row = seen_batch_signatures[batch_sig]
                dup_status = DuplicateStatus.EXACT.value
                dup_reason = f"Identical transaction duplicate of row #{prev_row} in same statement file."
                item["duplicate_status"] = dup_status
                item["duplicate_match_id"] = None
                item["duplicate_reason"] = dup_reason
                item["selected_for_import"] = False
                continue
            seen_batch_signatures[batch_sig] = item.get("source_row_number", 0)

            # Check Exact Match via Reference Number
            if c_ref and c_ref in by_ref:
                matched_tx = by_ref[c_ref]
                dup_status = DuplicateStatus.EXACT.value
                dup_match_id = matched_tx.id
                dup_reason = f"Exact match with existing transaction #{matched_tx.id} via reference '{c_ref}'."

            # Check Exact or Probable Match via Date, Amount, Direction
            elif c_date and c_paise:
                exact_key = f"{c_date}:{c_paise}:{c_dir}"
                if exact_key in by_triple:
                    candidates_list = by_triple[exact_key]
                    matched_tx = candidates_list[0]
                    
                    # If description or ref matches, exact; otherwise probable
                    if c_ref and matched_tx.external_reference and c_ref == matched_tx.external_reference.upper():
                        dup_status = DuplicateStatus.EXACT.value
                        dup_reason = f"Exact match on date, amount, and reference with #{matched_tx.id}."
                    elif c_desc and matched_tx.description and (c_desc in matched_tx.description.upper() or matched_tx.description.upper() in c_desc):
                        dup_status = DuplicateStatus.EXACT.value
                        dup_reason = f"Exact match on date, amount, and description with #{matched_tx.id}."
                    else:
                        dup_status = DuplicateStatus.PROBABLE.value
                        dup_reason = f"Probable match with #{matched_tx.id} on same date ({c_date}) and amount (₹{c_paise / 100:.2f})."
                    dup_match_id = matched_tx.id

            item["duplicate_status"] = dup_status
            item["duplicate_match_id"] = dup_match_id
            item["duplicate_reason"] = dup_reason

            # De-select exact duplicates by default while allowing user review
            if dup_status == DuplicateStatus.EXACT.value:
                item["selected_for_import"] = False

        return candidates
