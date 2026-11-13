# ARTHSAVORA — APPLICATION SERVICE GUIDELINES

## 1. Role and Responsibilities of Application Services

Application Services (`backend/app/services/`) serve as the orchestrators of business use cases in Arthsavora. They coordinate domain logic, persistence through repositories, authorization enforcement, and event emission.

```
       HTTP Request
            │
            ▼
┌───────────────────────────┐
│     FastAPI Endpoint      │  <-- Authenticates & Extracts Headers
└───────────┬───────────────┘
            │ passes WorkspaceContext & DTO
            ▼
┌───────────────────────────┐
│    Application Service    │  <-- Orchestration Engine:
│   (e.g. AccountService)   │      1. Validates domain preconditions via Value Objects
└─────┬───────────────┬─────┘      2. Enforces anti-IDOR workspace scoping
      │               │            3. Coordinates repositories
      ▼               ▼            4. Emits domain events
┌───────────┐   ┌───────────┐      5. Manages unit-of-work transactions
│  Domain   │   │Repository │
│  Invariants   │ (Database)│
└───────────┘   └───────────┘
```

---

## 2. Core Service Principles

### 2.1 Workspace Context Injection
Every multi-tenant service method **must** receive `WorkspaceContext` containing:
- `workspace`: The verified target workspace entity.
- `membership`: The user's active membership in this workspace.
- `current_user`: The authenticated caller.
- `role`: The active role (`owner`, `admin`, `member`, `accountant`, `viewer`).

Direct access to cross-workspace data without passing through `WorkspaceContext` is strictly forbidden.

### 2.2 Orchestration vs. Domain Logic
- **Belongs in Service:** Transaction boundaries (`session.commit()`), external idempotency deduplication, repository queries, dispatching domain events, translating external DTOs into domain objects.
- **Belongs in Domain:** Financial math (`Money`), transfer validation rules, refund limits, AI confidence thresholds.
- **Belongs in API Route:** HTTP status codes, parameter parsing, header resolution, cookie management.

### 2.3 Exception Translation
Application services must catch domain-level exceptions (`DomainError`, `DomainValidationError`, `CurrencyMismatchError`) and convert them into application-level exceptions (`ValidationException`, `NotFoundException`, `ConflictException`) so that the FastAPI global exception handlers produce standard RFC 7807 JSON error responses:
```python
try:
    Money.from_amount("0", currency=data.currency)
except DomainError as err:
    raise ValidationException(message=str(err), code="INVALID_CURRENCY")
```

---

## 3. Idempotency and Deduplication Pattern

Financial operations (transaction creation, statement imports, webhooks) must support idempotent retry semantics:
```python
if data.external_transaction_id:
    existing = await tx_repo.get_by_external_id(
        workspace_id=ws_id,
        external_id=data.external_transaction_id,
    )
    if existing:
        return existing, False  # (entity, is_new)
```
- When a client repeats a request with the same `external_transaction_id`, the existing record is returned without re-inserting or firing duplicate domain events.

---

## 4. Transaction Boundaries & Unit of Work

1. Each service method execution is bounded by an atomic database transaction.
2. If an error occurs, changes are rolled back automatically.
3. Domain events staged during the operation are only committed or dispatched to the message broker upon successful database commit.
