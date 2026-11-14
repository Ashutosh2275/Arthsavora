"""
Arthsavora Double-Entry Ledger Domain Service
Enforces strict double-entry balancing invariants, posted entry immutability, and reversal protocols.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationException, ConflictException, NotFoundException
from app.infrastructure.database.models.accounting import JournalEntry, JournalLine
from app.infrastructure.database.models.audit import AuditLog


def validate_journal_balanced(lines: list[JournalLine]) -> tuple[bool, Decimal, Decimal]:
    """
    Validates that total debits equal total credits across all lines in a journal entry.
    Returns (is_balanced, total_debits, total_credits).
    """
    if len(lines) < 2:
        raise ValidationException("A journal entry requires at least two lines (one debit and one credit).")

    total_debits = Decimal("0.0000")
    total_credits = Decimal("0.0000")

    for line in lines:
        amount = Decimal(str(line.amount))
        if amount <= Decimal("0.0000"):
            raise ValidationException(f"Line {line.line_number}: Journal line amount must be strictly greater than zero.")
        if line.entry_type == "debit":
            total_debits += amount
        elif line.entry_type == "credit":
            total_credits += amount
        else:
            raise ValidationException(f"Line {line.line_number}: Invalid entry_type '{line.entry_type}'. Must be 'debit' or 'credit'.")

    # Quantize to 4 decimal places for exact comparison
    debits_rounded = total_debits.quantize(Decimal("0.0001"))
    credits_rounded = total_credits.quantize(Decimal("0.0001"))

    is_balanced = debits_rounded == credits_rounded
    if not is_balanced:
        raise ValidationException(
            f"Unbalanced journal entry: Total debits (₹{debits_rounded}) must equal total credits (₹{credits_rounded}). "
            f"Difference: ₹{abs(debits_rounded - credits_rounded)}"
        )

    return True, debits_rounded, credits_rounded


async def post_journal_entry(
    session: AsyncSession,
    entry_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
) -> JournalEntry:
    """
    Transitions a draft journal entry into immutable posted status.
    Strictly verifies that total debits equal total credits before committing.
    """
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.id == entry_id)
        .options(selectinload(JournalEntry.lines))
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise NotFoundException(f"Journal entry {entry_id} not found.")

    if entry.status == "posted":
        raise ConflictException(f"Journal entry {entry.entry_number} is already posted and immutable.")

    if entry.status == "reversed":
        raise ConflictException(f"Journal entry {entry.entry_number} has been reversed and cannot be posted.")

    # Invariant Verification
    validate_journal_balanced(entry.lines)

    # State Transition
    entry.status = "posted"
    entry.posting_date = datetime.now(timezone.utc)

    # Audit Trail
    audit_entry = AuditLog(
        workspace_id=entry.workspace_id,
        actor_id=actor_id,
        action="POST_JOURNAL",
        entity_type="journal_entry",
        entity_id=entry.id,
        correlation_id=correlation_id,
        before_state={"status": "draft"},
        after_state={"status": "posted", "entry_number": entry.entry_number},
    )
    session.add(audit_entry)
    await session.flush()

    return entry


async def reverse_journal_entry(
    session: AsyncSession,
    entry_id: uuid.UUID,
    reversal_number: str,
    reason: str,
    actor_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
) -> JournalEntry:
    """
    Creates an immutable reversal journal entry flipping debits and credits of the original entry.
    Marks the original entry as 'reversed'.
    """
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.id == entry_id)
        .options(selectinload(JournalEntry.lines))
    )
    result = await session.execute(stmt)
    original_entry = result.scalar_one_or_none()

    if not original_entry:
        raise NotFoundException(f"Journal entry {entry_id} not found.")

    if original_entry.status != "posted":
        raise ConflictException(f"Only posted journal entries can be reversed. Current status: '{original_entry.status}'.")

    # Create Reversal Header
    now = datetime.now(timezone.utc)
    reversal_entry = JournalEntry(
        workspace_id=original_entry.workspace_id,
        entry_number=reversal_number,
        entry_date=now.date(),
        posting_date=now,
        status="posted",
        description=f"REVERSAL of {original_entry.entry_number}: {reason}",
        source_type="reversal",
        source_id=original_entry.id,
        reversal_of_entry_id=original_entry.id,
        created_by=actor_id,
    )
    session.add(reversal_entry)
    await session.flush()

    # Create Inverted Reversal Lines (debits become credits, credits become debits)
    for idx, orig_line in enumerate(original_entry.lines, start=1):
        inverted_type = "credit" if orig_line.entry_type == "debit" else "debit"
        reversal_line = JournalLine(
            journal_entry_id=reversal_entry.id,
            ledger_account_id=orig_line.ledger_account_id,
            line_number=idx,
            entry_type=inverted_type,
            amount=orig_line.amount,
            amount_paise=getattr(orig_line, "amount_paise", int(round(orig_line.amount * 100))),
            currency=orig_line.currency,
            description=f"Reversal of line {orig_line.line_number}",
        )
        session.add(reversal_line)

    # Mark original entry as reversed
    original_entry.status = "reversed"

    # Audit Trail
    audit_entry = AuditLog(
        workspace_id=original_entry.workspace_id,
        actor_id=actor_id,
        action="REVERSE_JOURNAL",
        entity_type="journal_entry",
        entity_id=reversal_entry.id,
        correlation_id=correlation_id,
        before_state={"original_entry_id": str(original_entry.id), "status": "posted"},
        after_state={"reversal_entry_id": str(reversal_entry.id), "status": "reversed", "reason": reason},
    )
    session.add(audit_entry)
    await session.flush()

    return reversal_entry
