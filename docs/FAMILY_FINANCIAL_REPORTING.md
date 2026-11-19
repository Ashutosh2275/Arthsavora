# ARTHSAVORA — FAMILY FINANCIAL REPORTING

## 1. Overview & Household Financial Visibility

Family financial reporting aggregates shared household expenditures, collaborative budget execution, and family member pool contributions within a shared household workspace boundary.

---

## 2. Shared vs Personal Boundary

```mermaid
flowchart TD
    subgraph PersonalWorkspaces["Private Personal Workspaces"]
        M1[Member 1: Private Transactions]
        M2[Member 2: Private Transactions]
        M3[Member 3: Private Transactions]
    end

    subgraph FamilyWorkspace["Shared Family Workspace Boundary"]
        FS[FamilyAccountShare<br/>Explicitly Shared Accounts]
        FA[Shared Expense Allocations]
        FC[Household Pool Contributions]
        FR[Consolidated Household Reports]
    end

    M1 -->|Opt-In Account Share| FS
    M2 -->|Opt-In Account Share| FS
    FS --> FR
    FA --> FR
    FC --> FR
    M3 -.->|Private Data Shielded| FamilyWorkspace
```

---

## 3. Household Financial Statements

### 3.1 Consolidated Family Income & Expense Report
- Aggregates shared household inflows (e.g. joint rental income, shared pool disbursements) and shared living costs (groceries, rent, utilities, family vacations, child tuition).
- Distinguishes shared household expenses from individual discretionary spending.

### 3.2 Member Contribution & Settlement Summary
- Tracks each family member's agreed monthly contribution vs actual contributions.
- Generates transparent settlement schedules without exposing unshared individual line items.

### 3.3 Data Privacy Rules
- Non-admin members (e.g. `member`, `child`) see only summary totals or categories permitted by their workspace role.
- Reports never leak private merchant descriptions or transaction notes from unshared personal accounts.
