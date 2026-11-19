# ARTHSAVORA Balance Synchronization Architecture

## 1. Overview

In personal and small-business financial management, an account balance is not a single scalar value. Financial institutions maintain multiple distinct balance concepts:
- **Ledger / Current Balance**: The total cleared money in the account.
- **Available Balance**: Spendable funds accounting for pending holds, uncleared checks, and overdraft buffers.
- **Credit Card Liability**: Outstanding charges currently due to the card issuer.
- **Credit Limit**: Total authorized borrowing capacity.

ARTHSAVORA maintains strict clarity between **external bank-reported balances** and **internal general ledger book balances**.

---

## 2. Distinction Between Reported Balance and Book Balance

| Attribute | Provider Reported Balance | Internal Book Balance |
| :--- | :--- | :--- |
| **Field Name** | `provider_reported_balance_paise` | `current_book_balance_paise` |
| **Source** | External bank / Account Aggregator API | Sum of all posted ledger transactions in ARTHSAVORA |
| **Authority** | External banking institution | Internal double-entry accounting ledger |
| **Update Mechanism** | Sync job via `FinancialProviderAdapter.fetch_balances` | Journal entries and posted `Transaction` entities |
| **Mutability** | Updated on every sync run | Altered only by verified financial transactions |
| **Role in System** | Informational baseline for audit & reconciliation | Authoritative truth for reports, budgets, and cash flow |

> [!IMPORTANT]
> The provider-reported balance **never** directly overwrites the internal book balance. Overwriting book balances destroys double-entry accounting integrity and conceals missing or duplicated transactions. Differences between the two are captured as **Reconciliation Variances**.

---

## 3. Balance Snapshots (`AccountBalanceSnapshot`)

To provide auditability, point-in-time reconstruction, and historical net worth curves, every balance synchronization event generates an immutable `AccountBalanceSnapshot` record:

```python
snapshot = AccountBalanceSnapshot(
    id=uuid4(),
    account_id=account.id,
    workspace_id=workspace_id,
    balance_type="provider_reported",
    balance_amount=Decimal(rep_balance) / Decimal(100),
    balance_paise=rep_balance,
    currency=account.currency,
    effective_at=datetime.now(timezone.utc),
    source="account_aggregator",
    source_reference=str(connection.id),
    reconciliation_status="reconciled",
)
```

### Snapshot Attributes:
- `balance_type`: `provider_reported`, `book`, `available`, or `liability`.
- `balance_paise`: Exact integer minor units.
- `effective_at`: Accurate timestamp provided by the financial institution.
- `source`: Provenance tag (`account_aggregator`, `manual`, `statement`).
- `source_reference`: ID of the sync job or connection that acquired the balance.

---

## 4. Credit Card & Liability Synchronization

For credit card accounts:
- Current balance represents **outstanding liability** (`outstanding_liability_paise`).
- Available credit is tracked (`available_credit_paise`).
- Next payment due date is extracted from statement feeds where available.
- Payments towards credit cards register as transfers from deposit accounts, reducing outstanding liability and matching the bank-reported reduction upon sync.
