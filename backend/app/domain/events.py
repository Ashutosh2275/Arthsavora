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
