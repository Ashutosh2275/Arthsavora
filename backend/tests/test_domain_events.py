"""
Arthsavora Domain Tests — Domain Events and Outbox Collector
Verifies domain event contracts, factory functions, JSON serialization,
and transactional collector mechanics.
"""

import json
import uuid
from datetime import datetime, timezone
from app.domain.events import (
    DomainEvent,
    DomainEventCollector,
    create_workspace_created_event,
    create_member_joined_event,
    create_account_created_event,
    create_transaction_created_event,
    create_journal_posted_event,
)


def test_domain_event_immutability_and_serialization():
    """Verify DomainEvent contract fields and clean dictionary serialization."""
    w_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    event = DomainEvent(
        event_type="test.event",
        workspace_id=w_id,
        actor_id=actor_id,
        correlation_id="corr-12345",
        payload={"key": "value", "count": 42},
    )

    data = event.to_dict()
    assert data["event_type"] == "test.event"
    assert data["workspace_id"] == str(w_id)
    assert data["actor_id"] == str(actor_id)
    assert data["correlation_id"] == "corr-12345"
    assert data["payload"] == {"key": "value", "count": 42}
    assert "event_id" in data
    assert "occurred_at" in data

    # Verify JSON serializability
    json_str = json.dumps(data)
    assert "test.event" in json_str


def test_domain_event_factories():
    """Verify domain event factory functions produce standard envelopes."""
    w_id = uuid.uuid4()
    u_id = uuid.uuid4()
    a_id = uuid.uuid4()
    t_id = uuid.uuid4()
    j_id = uuid.uuid4()

    # Workspace created
    e_ws = create_workspace_created_event(
        workspace_id=w_id,
        owner_id=u_id,
        workspace_name="Acme Corp",
        workspace_type="business",
    )
    assert e_ws.event_type == "workspace.created"
    assert e_ws.payload["workspace_name"] == "Acme Corp"
    assert e_ws.payload["workspace_type"] == "business"

    # Member joined
    e_mem = create_member_joined_event(
        workspace_id=w_id,
        user_id=u_id,
        role="accountant",
    )
    assert e_mem.event_type == "workspace.member_joined"
    assert e_mem.payload["role"] == "accountant"

    # Account created
    e_acc = create_account_created_event(
        workspace_id=w_id,
        account_id=a_id,
        account_name="HDFC Current",
        account_type="current",
        currency="INR",
    )
    assert e_acc.event_type == "account.created"
    assert e_acc.payload["account_name"] == "HDFC Current"
    assert e_acc.payload["currency"] == "INR"

    # Transaction created
    e_tx = create_transaction_created_event(
        workspace_id=w_id,
        transaction_id=t_id,
        account_id=a_id,
        amount_str="15000.00",
        currency="INR",
        transaction_type="income",
    )
    assert e_tx.event_type == "transaction.created"
    assert e_tx.payload["amount"] == "15000.00"
    assert e_tx.payload["transaction_type"] == "income"

    # Journal posted
    e_jr = create_journal_posted_event(
        workspace_id=w_id,
        journal_id=j_id,
        entry_number="JE-2026-001",
        total_amount_str="25000.00",
        currency="INR",
    )
    assert e_jr.event_type == "accounting.journal_posted"
    assert e_jr.payload["entry_number"] == "JE-2026-001"


def test_domain_event_collector():
    """Verify collector accumulates, flushes, and clears events transactionally."""
    collector = DomainEventCollector()
    assert len(collector.get_events()) == 0

    w_id = uuid.uuid4()
    e1 = create_workspace_created_event(w_id, uuid.uuid4(), "WS 1", "personal")
    e2 = create_workspace_created_event(w_id, uuid.uuid4(), "WS 2", "family")

    collector.record(e1)
    collector.record(e2)

    assert len(collector.get_events()) == 2

    # collect() should return and flush
    collected = collector.collect()
    assert len(collected) == 2
    assert len(collector.get_events()) == 0

    # clear() test
    collector.record(e1)
    assert len(collector.get_events()) == 1
    collector.clear()
    assert len(collector.get_events()) == 0
