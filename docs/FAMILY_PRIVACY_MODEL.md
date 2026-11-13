# ARTHSAVORA — FAMILY WORKSPACE PRIVACY & ISOLATION MODEL

## 1. Executive Summary

Financial collaboration within households is inherently nuanced. While families need to share joint expenses (rent, groceries, child education, utility bills), individuals demand strict privacy over discretionary personal spending, private investments, and confidential accounts.

The **Arthsavora Family Privacy Model** establishes zero-trust boundaries: family membership grants access **only** to accounts and records explicitly created within or shared to the Family Workspace. Personal financial environments remain completely segregated and tamper-proof.

---

## 2. Core Boundary Principles

```mermaid
graph TD
    subgraph User A Personal Context
        A_WS["Personal Workspace (User A)"]
        A_Acc["Private Bank Account\n(Salary / Discretionary)"]
        A_Tx["Private Transactions"]
        A_WS --> A_Acc --> A_Tx
    end

    subgraph User B Personal Context
        B_WS["Personal Workspace (User B)"]
        B_Acc["Private Bank Account\n(Personal Card / Mutual Funds)"]
        B_Tx["Private Transactions"]
        B_WS --> B_Acc --> B_Tx
    end

    subgraph Shared Family Context
        Fam_WS["Family Workspace\n(Household Entity)"]
        Shared_Acc["Shared Bank Account\n(Joint Household Expenses)"]
        Shared_Tx["Shared Transactions\n(Groceries, Utilities, Rent)"]
        Fam_WS --> Shared_Acc --> Shared_Tx
    end

    UserA["User A (Family Head)"] -.->|Owner/Admin| Fam_WS
    UserB["User B (Family Member)"] -.->|Member| Fam_WS
    UserA ==>|Full Access| A_WS
    UserB ==>|Full Access| B_WS

    UserA -.x|BLOCKED BY RLS / IDOR DEFENSE| B_WS
    UserB -.x|BLOCKED BY RLS / IDOR DEFENSE| A_WS
```

### 2.1 The Inviolable Isolation Rules
1. **Personal Accounts Remain Private by Default:** An account created in User A's Personal Workspace belongs solely to User A. No family member or family admin can inspect, query, or audit it.
2. **Distinct Workspace Entity:** The Family Workspace has its own independent `workspace_id`. All ledger entries, journal postings, and balance sheets are scoped strictly to this ID.
3. **No Automatic Account Leakage:** Joining a Family Workspace does **not** expose or link any personal accounts.
4. **Explicit Shared Accounts:** Only accounts opened directly inside the Family Workspace (or explicitly shared with cryptographic consent) are visible to members.
5. **Anti-IDOR Defense:** Even if User A is the creator and owner of the Family Workspace, any attempt by User A to supply User B's personal workspace ID or account ID returns **HTTP 404 Not Found**.

---

## 3. Role Privileges in Family Workspaces

| Capability | Family Head (Owner / Admin) | Family Member (Partner / Adult) | Family Viewer (Dependent / Child) |
| :--- | :---: | :---: | :---: |
| View Shared Household Balances | Yes | Yes | Yes |
| View Shared Transaction History | Yes | Yes | Yes |
| Record Shared Household Expenses | Yes | Yes | No (Read-Only) |
| Categorize & Tag Shared Expenses | Yes | Yes | No |
| Add / Remove Family Members | Yes | No | No |
| Change Member Roles | Yes | No | No |
| Create Shared Household Accounts | Yes | No | No |
| View Other Members' Personal Finances | **NEVER (Blocked)** | **NEVER (Blocked)** | **NEVER (Blocked)** |

---

## 4. Verification and Enforcement Architecture

Every API request carrying financial queries (`/accounts`, `/transactions`, `/budgets`) requires the `X-Workspace-ID` header. The backend enforces:
1. **Membership Verification:** Checks `workspace_members` for an `active` record matching `(workspace_id, current_user.id)`. If missing, returns `404 Not Found` (preventing tenant enumeration).
2. **Transaction-Local RLS Policy:** Activates PostgreSQL Row-Level Security:
   ```sql
   SET LOCAL arthsavora.current_tenant_id = '<resolved_family_workspace_id>';
   ```
3. **Database-Level Segregation:** PostgreSQL RLS policies discard all rows whose `workspace_id != arthsavora.current_tenant_id`, guaranteeing mathematical isolation even in the event of an application-level query error.
