# ARTHSAVORA — DOMAIN EVENTS & TRANSACTIONAL OUTBOX ARCHITECTURE

## 1. Objective

Domain events capture authoritative facts that have occurred within the Arthsavora domain boundaries. They enable loose coupling between domain operations, audit logging, notification dispatch, analytics tracking, and background asynchronous jobs.

---

## 2. Event Contract Specification

Every domain event in Arthsavora is an immutable dataclass (`DomainEvent` in `backend/app/domain/events.py`):

| Field | Type | Description |
| :--- | :--- | :--- |
| `event_id` | `UUID` | Unique UUIDv4 identifier for deduplication and tracing. |
| `event_type` | `str` | Hierarchical event identifier (e.g. `transaction.created`). |
| `version` | `int` | Event schema version (defaults to `1`). |
| `occurred_at` | `datetime` | UTC timestamp with timezone. |
| `workspace_id` | `UUID` | Target tenant workspace boundary. |
| `actor_id` | `UUID?` | User who initiated the action (if user-triggered). |
| `correlation_id` | `str?` | Distributed request trace ID (`X-Request-ID`). |
| `payload` | `dict` | Event-specific data payload. |

---

## 3. Event Taxonomy

```
arthsavora.events
├── workspace
│   ├── workspace.created             # New tenant workspace initialized
│   └── workspace.member_joined       # User accepted invite / added to workspace
├── account
│   └── account.created               # Bank, cash, or card account provisioned
├── transaction
│   └── transaction.created           # Financial movement recorded or imported
└── accounting
    └── accounting.journal_posted     # Balanced double-entry journal finalized
```

---

## 4. The Transactional Outbox Pattern

To prevent the **dual-write problem** (where a database commit succeeds but message publishing fails, or vice-versa), Arthsavora utilizes the Transactional Outbox pattern:

```
[ HTTP Request ]
      │
      ▼
[ Application Service ]
      │
      ├─ 1. Performs Domain Logic
      ├─ 2. Writes Entity to PostgreSQL Session
      └─ 3. Collects DomainEvent in DomainEventCollector
      │
      ▼
[ Database Transaction Commit ]
      │
      ├─ SUCCESS: Flush and publish collected events (Celery / Redis / Kafka)
      └─ ROLLBACK: Clear collected events with zero ghost dispatches
```

### 4.1 Collector Interface (`DomainEventCollector`)
```python
collector = DomainEventCollector()

# Stage event during use case
collector.record(event)

# On transaction commit
events_to_dispatch = collector.collect()  # Flushes internal list

# On transaction error / rollback
collector.clear()  # Discards staged events
```

---

## 5. Event Ingestion & Idempotent Handlers

Downstream consumers (Celery workers, audit sinks, notification agents) must handle events idempotently:
1. Every event carries a persistent `event_id`.
2. Sinks check if `event_id` has already been processed before executing side effects.
3. If processed, the message is acknowledged and skipped without duplicate actions.
