# ARTHSAVORA — DOMAIN ARCHITECTURE SPECIFICATION

## 1. Executive Summary

This document establishes the architecture, boundaries, dependency rules, and design patterns governing the Core Domain Layer of **Arthsavora**, an India-first AI-powered commercial financial management platform. 

The domain layer encapsulates all authoritative business entities, financial calculation logic, business invariants, and domain events. It is architected according to Clean Architecture and Domain-Driven Design (DDD) principles within a modular monolith structure.

---

## 2. Architectural Layering & Dependency Inversion

Arthsavora enforces strict unidirectional dependency rules:

```
┌─────────────────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                          │
│   FastAPI Endpoints, Route Handlers, HTTP Middleware       │
└──────────────────────────────┬──────────────────────────────┘
                               │ depends on
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 APPLICATION SERVICES LAYER                  │
│   AccountService, TransactionService, Orchestration         │
└──────────────────────────────┬──────────────────────────────┘
                               │ depends on
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   CORE DOMAIN LAYER                         │
│   Money Value Object, Domain Invariants, Domain Events,     │
│   Pure Domain Exceptions, Aggregate Contracts               │
│   (ZERO dependencies on HTTP, FastAPI, or External SDKs)    │
└──────────────────────────────▲──────────────────────────────┘
                               │ implements / persists
┌──────────────────────────────┴──────────────────────────────┐
│                 INFRASTRUCTURE LAYER                        │
│   PostgreSQL Repositories, SQLAlchemy Models, Cache, Celery │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Rules:
1. **Domain Independence:** The Core Domain (`backend/app/domain/`) has **zero dependencies** on FastAPI, HTTP status codes, Celery, Redis, or external third-party SDKs. It depends strictly on the Python standard library (`decimal`, `dataclasses`, `datetime`, `uuid`).
2. **Persistence Ignorance:** Domain calculations and invariant rules operate on domain models and value objects without knowledge of whether or how data is persisted.
3. **Application Service Orchestration:** Application services (`backend/app/services/`) translate incoming data, invoke domain rules, orchestrate repository persistence, collect domain events, and manage transaction commits.

---

## 3. Directory Layout & Module Structure

```
backend/app/
├── domain/                      # Pure Domain Layer
│   ├── __init__.py              # Central domain exports
│   ├── exceptions.py            # Pure domain exceptions hierarchy
│   ├── money.py                 # Exact Money Value Object & Bankers Rounding
│   ├── events.py                # DomainEvent dataclass & outbox collector
│   └── rules.py                 # Pure business invariants & financial guards
├── repositories/                # Persistence & Data Access Layer
│   ├── __init__.py              # Repository exports
│   ├── base.py                  # BaseRepository[T] generic contract
│   ├── workspace_scoped.py      # WorkspaceScopedRepository[T] anti-IDOR tenant isolation
│   ├── workspace_repository.py  # Workspace & membership persistence
│   ├── account_repository.py    # Bank/cash/wallet account queries
│   └── transaction_repository.py# Transaction queries & deduplication
├── services/                    # Application Services Layer
│   ├── account_service.py       # Account lifecycle orchestration
│   ├── transaction_service.py   # Transaction intake & deduplication
│   └── ...                      # Auth, intelligence, and system services
├── schemas/                     # API Contracts (Pydantic v2)
│   ├── account.py               # Account create/response schemas
│   ├── transaction.py           # Transaction create/response schemas
│   └── ...                      # Common & auth schemas
└── api/v1/                      # Presentation Layer
    ├── accounts.py              # Account endpoints (/api/v1/accounts/)
    ├── transactions.py          # Transaction endpoints (/api/v1/transactions/)
    └── router.py                # Consolidated V1 router
```

---

## 4. Domain Layer Components

### 4.1 Value Objects
Value objects are immutable objects defined solely by their attributes with no conceptual identity.
- **`Money`:** Encapsulates an exact `Decimal` amount and an ISO 4217 currency string (`INR`, `USD`, etc.). Prohibits float arithmetic, enforces Bankers Rounding (`ROUND_HALF_EVEN`), and guarantees cross-currency arithmetic safety.

### 4.2 Entities & Aggregates
- **Account:** Represents a physical or virtual repository of financial value (Savings Bank, Current Account, Cash Wallet, Credit Card, Loan).
- **Transaction:** Represents an authoritative movement of money across accounts or external parties. Enforces idempotency via `external_transaction_id`.
- **Workspace:** The root multi-tenant security boundary. All accounts, transactions, categories, and journals belong strictly to a single workspace.

### 4.3 Domain Invariants & Rules (`app.domain.rules`)
- **Internal Transfers:** Source and destination accounts cannot be identical; transfer amount must be strictly positive; currencies must match or have an explicit exchange conversion.
- **Refunds:** Refund amount cannot exceed original transaction amount.
- **AI Predictions:** Predictions must explicitly record model identifier, model version, and confidence score ($0.0 \le \text{confidence} \le 1.0$), with human verification tracking.

### 4.4 Domain Events (`app.domain.events`)
Authoritative record of state transitions within domain boundaries, designed for transactional outbox staging:
- `workspace.created`
- `workspace.member_joined`
- `account.created`
- `transaction.created`
- `accounting.journal_posted`

---

## 5. Security & Isolation Invariants

1. **Anti-IDOR Querying:** Every read and mutation in the repository layer scopes SQL queries by `workspace_id`. An attacker supplying a valid UUID belonging to another workspace receives `404 Not Found` with zero existence leakage.
2. **Tenant RLS Context:** PostgreSQL Row-Level Security session variables (`app.current_workspace_id`) are maintained alongside application-level checks.
3. **Deterministic Financial Calculation:** All amounts are parsed through `Money` before arithmetic or ledger entry generation.
