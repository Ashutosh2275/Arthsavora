# Accounting Reconciliation and Integrity Testing

## 1. Scope of Reconciliation Testing

Accounting reconciliation guarantees that the operational transactional store (`Transaction`, `Account`) and the authoritative double-entry general ledger (`JournalEntry`, `JournalLine`) remain in continuous mathematical alignment.

```mermaid
flowchart LR
    A[Operational Transaction] -->|Automatic Mapping| B[Double-Entry Journal Entry]
    B --> C[Debit Journal Line]
    B --> D[Credit Journal Line]
    C --> E[General Ledger & Trial Balance]
    D --> E
    E --> F{Reconciliation Check: Sum(D) == Sum(C)?}
    F -->|Zero Delta| G[Reconciled & Certified]
    F -->|Non-Zero Delta| H[Unbalanced Journal Error Raised]
```

---

## 2. Tested Reconciliation Scenarios

### 2.1 Multi-Account Transfer Reconciliation
- **Scenario**: Transfer of ₹15,000 from Savings Account to Credit Card.
- **Verification**:
  - Source Account (`Asset:Savings`): Credited ₹15,000 (Balance decreases by 15,000).
  - Target Account (`Liability:CreditCard`): Debited ₹15,000 (Liability decreases by 15,000).
  - Net Balance Sheet Impact: Asset decreased by ₹15,000; Liability decreased by ₹15,000; Net Equity unchanged.
  - Trial Balance delta: Zero discrepancy.

### 2.2 Reversal and Voiding Invariance
- **Scenario**: Erroneously posted commercial invoice payment reversed after 48 hours.
- **Verification**:
  - Reversal creates an immutable counter-journal entry with inverted debits and credits.
  - Original entries are never deleted or modified in-place (Append-Only Ledger Principle).
  - Historical audit trail remains unbroken and verifiable by external auditors.

### 2.3 Concurrent Journal Postings
- **Scenario**: 50 concurrent transactions posted simultaneously across shared bank and expense accounts.
- **Verification**:
  - PostgreSQL row-level locks on account balance updates prevent lost updates.
  - Running ledger balance strictly equals the algebraic sum of all posted journal lines.
