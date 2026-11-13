# ARTHSAVORA — WORKSPACE MANAGEMENT & MULTI-TENANCY ARCHITECTURE

## 1. Executive Summary

Arthsavora provides multi-tenant financial isolation using a flexible workspace architecture. Every financial entity (an individual, a household, a freelancer, or a small business) operates inside a dedicated `Workspace`. Users can hold distinct roles across multiple workspaces without data leakage.

---

## 2. Workspace Tenancy Models

Arthsavora natively supports three workspace types, each tailored to distinct operational and statutory requirements:

```mermaid
flowchart TD
    User["User Identity (UUID)"]
    
    User -->|1:1 Primary| Personal["Personal Workspace (1 Max)\n- Strict Privacy\n- Personal Bank Accounts\n- Discretionary Budgets"]
    User -->|1:N Collaborator| Family["Family Workspace (N Allowed)\n- Household Expenses\n- Shared Allowances\n- Explicit Account Linkage"]
    User -->|1:N Owner/Admin/Staff| Business["Business Workspace (N Allowed)\n- GSTIN & PAN Statutory Tracking\n- Double-Entry General Ledger\n- Invoicing & Vendor Management"]
```

### 2.1 Personal Workspace
- **Tenancy Invariant:** Strictly **one** active personal workspace per user. Attempting to create an additional personal workspace raises `409 Conflict` (`DUPLICATE_PERSONAL_WORKSPACE`).
- **Provisioning:** Automatically created during user onboarding or initial registration.
- **Privacy Boundary:** Personal financial records (accounts, transactions, balances, credit lines) are completely private and cannot be inspected by family admins or business partners.

### 2.2 Family Workspace
- **Collaborative Household Scope:** Enables partners, dependents, and extended family to coordinate budgets and bills without compromising individual personal privacy.
- **Privacy Model:** Personal accounts do **not** automatically sync to family workspaces. Only accounts created explicitly inside the family workspace are visible to family members.
- **Roles Supported:** `owner`, `admin`, `member`, `viewer`.

### 2.3 Business Workspace
- **Commercial & Statutory Scope:** Supports freelancers, consultants, LLPs, partnerships, and private limited entities.
- **Statutory Profile Capture:**
  - `legal_business_name`: Registered legal entity name.
  - `trade_name`: Operating brand name.
  - `entity_type`: `freelancer`, `sole_proprietorship`, `partnership`, `llp`, `pvt_ltd`.
  - `gstin`: 15-character Goods and Services Tax Identification Number.
  - `pan`: 10-character Permanent Account Number.
  - `industry`: Business sector classification.
  - `financial_year_start_month`: Defaults to 4 (April 1st to March 31st for India).
- **Roles Supported:** `owner`, `admin`, `accountant`, `approver`, `staff`, `viewer`.

---

## 3. Workspace Lifecycle State Machine

Workspaces undergo strict state transitions governed by business rules and role authorization:

```mermaid
stateDiagram-v2
    [*] --> CREATING
    CREATING --> ACTIVE: Provisioning Completed
    ACTIVE --> SUSPENDED: Non-Compliance / Admin Lock
    SUSPENDED --> ACTIVE: Compliance Restored
    ACTIVE --> ARCHIVED: Owner/Admin Archive Request
    ARCHIVED --> ACTIVE: Owner/Admin Restore Request
    ARCHIVED --> DELETION_PENDING: Grace Period Initiated (30 Days)
    DELETION_PENDING --> DELETED: Soft-Deletion Completed
    DELETED --> [*]
```

### 3.1 Lifecycle States

| State | Mutating Actions Allowed? | Read Access Allowed? | Description |
| :--- | :--- | :--- | :--- |
| `CREATING` | No | Internal only | Background provisioning and ledger seeding |
| `ACTIVE` | Yes (per role permissions) | Yes (per role) | Normal operational state |
| `SUSPENDED` | No | No | Access blocked due to statutory/safety violation |
| `ARCHIVED` | No (read-only) | Yes (authorized members) | Deactivated project; records preserved for audit |
| `DELETION_PENDING`| No | No | 30-day recovery holding state before deletion |
| `DELETED` | No | No | Soft-deleted; hidden from all standard queries |

### 3.2 State Transition Enforcement
- `POST /api/v1/workspaces/{id}/archive`: Transitions `ACTIVE` -> `ARCHIVED`. Rejects transitions from any status other than `ACTIVE` with `422 Unprocessable Entity` (`INVALID_STATE_TRANSITION`).
- `POST /api/v1/workspaces/{id}/restore`: Transitions `ARCHIVED` -> `ACTIVE`. Rejects transitions from any status other than `ARCHIVED` with `422 Unprocessable Entity` (`INVALID_STATE_TRANSITION`).
- All transitions generate immutable audit trail entries in `audit_logs`.

---

## 4. Controlled Ownership Transfer Protocol

To guarantee financial continuity, a workspace can never exist in an ownerless state. Ownership handover is executed as an atomic database transaction:

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Current Owner
    participant API as FastAPI Backend
    participant DB as PostgreSQL 18
    actor Successor as Designated Successor

    Owner->>API: POST /workspaces/{id}/ownership-transfer<br/>{new_owner_id, previous_owner_role: "admin", confirm: true}
    Note over API: Verify caller is current Owner<br/>Verify confirm=true<br/>Verify successor is active member
    API->>DB: BEGIN TRANSACTION (SERIALIZABLE)
    API->>DB: UPDATE workspaces SET owner_id = :successor_user_id
    API->>DB: UPDATE workspace_members SET role = 'owner' WHERE user_id = :successor_user_id
    API->>DB: UPDATE workspace_members SET role = :previous_owner_role WHERE user_id = :caller_id
    API->>DB: INSERT INTO audit_logs (action='workspace:transfer_ownership')
    API->>DB: COMMIT TRANSACTION
    API-->>Owner: 200 OK (Updated Workspace Metadata)
```

### Invariants:
1. **Single Owner Rule:** A workspace has exactly one user marked as `owner_id`.
2. **Successor Pre-requisite:** The target owner must already be an active member of the workspace.
3. **Explicit Confirmation:** Must supply `{"confirm": true}` in the request payload.
4. **Self-Transfer Prohibition:** Attempting to transfer ownership to oneself is rejected with `422 Validation Error`.
5. **No Owner Removal:** An owner cannot be revoked or deleted from `workspace_members` without first transferring ownership to another active member.
