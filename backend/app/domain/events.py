"""
Arthsavora Domain Events & Transactional Outbox Foundation
Defines standard domain event contracts, serialization envelopes,
and in-memory outbox collectors to guarantee safe event dispatch.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass(frozen=True)
class DomainEvent:
    """
    Immutable domain event contract.
    Represents an authoritative state change that has occurred within a domain boundary.
    """

    event_type: str
    workspace_id: uuid.UUID
    payload: Dict[str, Any]
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    version: int = 1
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: Optional[uuid.UUID] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts domain event to a JSON-serializable dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "version": self.version,
            "occurred_at": self.occurred_at.isoformat(),
            "workspace_id": str(self.workspace_id),
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }


# ---------------------------------------------------------------------------
# Specific Domain Event Factories
# ---------------------------------------------------------------------------


def create_workspace_created_event(
    workspace_id: uuid.UUID,
    owner_id: uuid.UUID,
    workspace_name: str,
    workspace_type: str,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="workspace.created",
        workspace_id=workspace_id,
        actor_id=owner_id,
        correlation_id=correlation_id,
        payload={
            "workspace_name": workspace_name,
            "workspace_type": workspace_type,
            "owner_id": str(owner_id),
        },
    )


def create_member_joined_event(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="workspace.member_joined",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "user_id": str(user_id),
            "role": role,
        },
    )


def create_account_created_event(
    workspace_id: uuid.UUID,
    account_id: uuid.UUID,
    account_name: str,
    account_type: str,
    currency: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="account.created",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "account_id": str(account_id),
            "account_name": account_name,
            "account_type": account_type,
            "currency": currency,
        },
    )


def create_transaction_created_event(
    workspace_id: uuid.UUID,
    transaction_id: uuid.UUID,
    account_id: uuid.UUID,
    amount_str: str,
    currency: str,
    transaction_type: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="transaction.created",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "transaction_id": str(transaction_id),
            "account_id": str(account_id),
            "amount": amount_str,
            "currency": currency,
            "transaction_type": transaction_type,
        },
    )


def create_transaction_posted_event(
    workspace_id: uuid.UUID,
    transaction_id: uuid.UUID,
    account_id: uuid.UUID,
    amount_str: str,
    currency: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="transaction.posted",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "transaction_id": str(transaction_id),
            "account_id": str(account_id),
            "amount": amount_str,
            "currency": currency,
        },
    )


def create_transaction_cancelled_event(
    workspace_id: uuid.UUID,
    transaction_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="transaction.cancelled",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "transaction_id": str(transaction_id),
            "reason": reason,
        },
    )


def create_transaction_reversed_event(
    workspace_id: uuid.UUID,
    original_transaction_id: uuid.UUID,
    reversal_transaction_id: uuid.UUID,
    reason: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="transaction.reversed",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "original_transaction_id": str(original_transaction_id),
            "reversal_transaction_id": str(reversal_transaction_id),
            "reason": reason,
        },
    )


def create_transaction_refunded_event(
    workspace_id: uuid.UUID,
    original_transaction_id: uuid.UUID,
    refund_transaction_id: uuid.UUID,
    refund_amount_str: str,
    currency: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="transaction.refunded",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "original_transaction_id": str(original_transaction_id),
            "refund_transaction_id": str(refund_transaction_id),
            "refund_amount": refund_amount_str,
            "currency": currency,
        },
    )


def create_transfer_created_event(
    workspace_id: uuid.UUID,
    transfer_id: uuid.UUID,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    amount_str: str,
    currency: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="transfer.created",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "transfer_id": str(transfer_id),
            "source_account_id": str(source_account_id),
            "destination_account_id": str(destination_account_id),
            "amount": amount_str,
            "currency": currency,
        },
    )


def create_journal_posted_event(
    workspace_id: uuid.UUID,
    journal_id: uuid.UUID,
    entry_number: str,
    total_amount_str: str,
    currency: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="accounting.journal_posted",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "journal_id": str(journal_id),
            "entry_number": entry_number,
            "total_amount": total_amount_str,
            "currency": currency,
        },
    )


def create_journal_created_event(
    workspace_id: uuid.UUID,
    journal_id: uuid.UUID,
    entry_number: str,
    source_type: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="accounting.journal_created",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "journal_id": str(journal_id),
            "entry_number": entry_number,
            "source_type": source_type,
        },
    )


def create_journal_reversed_event(
    workspace_id: uuid.UUID,
    original_journal_id: uuid.UUID,
    reversal_journal_id: uuid.UUID,
    reversal_number: str,
    reason: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="accounting.journal_reversed",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "original_journal_id": str(original_journal_id),
            "reversal_journal_id": str(reversal_journal_id),
            "reversal_number": reversal_number,
            "reason": reason,
        },
    )


def create_period_closed_event(
    workspace_id: uuid.UUID,
    period_id: uuid.UUID,
    fiscal_year: str,
    period_number: int,
    period_name: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="accounting.period_closed",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "period_id": str(period_id),
            "fiscal_year": fiscal_year,
            "period_number": period_number,
            "period_name": period_name,
        },
    )


def create_import_job_created_event(
    workspace_id: uuid.UUID,
    job_id: uuid.UUID,
    source_type: str,
    original_filename: Optional[str],
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="import.job_created",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "job_id": str(job_id),
            "source_type": source_type,
            "original_filename": original_filename,
        },
    )


def create_import_job_completed_event(
    workspace_id: uuid.UUID,
    job_id: uuid.UUID,
    total_records: int,
    imported_records: int,
    duplicate_records: int,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="import.job_completed",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "job_id": str(job_id),
            "total_records": total_records,
            "imported_records": imported_records,
            "duplicate_records": duplicate_records,
        },
    )


def create_import_job_failed_event(
    workspace_id: uuid.UUID,
    job_id: uuid.UUID,
    error_summary: str,
    actor_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="import.job_failed",
        workspace_id=workspace_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "job_id": str(job_id),
            "error_summary": error_summary,
        },
    )



def create_category_created_event(
    workspace_id: uuid.UUID,
    category_id: uuid.UUID,
    name: str,
    category_type: str,
    actor_id: Optional[uuid.UUID] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="category.created",
        workspace_id=workspace_id,
        actor_id=actor_id,
        payload={
            "category_id": str(category_id),
            "name": name,
            "category_type": category_type,
        },
    )


def create_transaction_categorized_event(
    workspace_id: uuid.UUID,
    transaction_id: uuid.UUID,
    category_id: uuid.UUID,
    method: str,
    confidence_score: float,
    actor_id: Optional[uuid.UUID] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="transaction.categorized",
        workspace_id=workspace_id,
        actor_id=actor_id,
        payload={
            "transaction_id": str(transaction_id),
            "category_id": str(category_id),
            "method": method,
            "confidence_score": confidence_score,
        },
    )


def create_classification_feedback_event(
    workspace_id: uuid.UUID,
    transaction_id: uuid.UUID,
    feedback_action: str,
    confirmed_category_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
) -> DomainEvent:
    return DomainEvent(
        event_type="intelligence.feedback_recorded",
        workspace_id=workspace_id,
        actor_id=actor_id,
        payload={
            "transaction_id": str(transaction_id),
            "feedback_action": feedback_action,
            "confirmed_category_id": str(confirmed_category_id),
        },
    )


# ---------------------------------------------------------------------------
# Outbox Collector
# ---------------------------------------------------------------------------


class DomainEventCollector:
    """
    Thread-safe/session-scoped collector that holds domain events during a unit of work.
    Guarantees events are released only after the surrounding database transaction commits.
    """

    def __init__(self):
        self._events: List[DomainEvent] = []

    def record(self, event: DomainEvent) -> None:
        """Stages a new domain event."""
        self._events.append(event)

    def get_events(self) -> List[DomainEvent]:
        """Returns all staged domain events."""
        return list(self._events)

    def clear(self) -> None:
        """Discards all staged events (e.g. on transaction rollback)."""
        self._events.clear()

    def collect(self) -> List[DomainEvent]:
        """Returns and flushes all staged events."""
        events = list(self._events)
        self._events.clear()
        return events
