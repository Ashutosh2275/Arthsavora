# Arthsavora — Transaction Lifecycle & State Machine

## 1. Lifecycle State Machine Overview

Financial accuracy requires that every transaction follows a deterministic, audited lifecycle. In Arthsavora, transactions are treated as stateful financial records governed by a Finite State Machine (FSM). 

The lifecycle guarantees that balance mutations occur in lockstep with state changes, and that historical ledger entries cannot be arbitrarily altered or deleted.

```
       +-----------------------+
       |   Transaction Intake  |
       +-----------+-----------+
                   |
         +---------+---------+
         |                   |
         v                   v
   [ pending ]         [ posted ] <--------------------+
         |                   |                         |
         +----+----+         | (Compensating Reversal) |
         |         |         v                         |
         v         v    [ reversed ]                   |
    [ failed ] [ cancelled ]                           |
                                                       |
               (Direct Intake for Manual / Settled) ---+
```

---

## 2. Authorized States & Descriptions

| State | Classification | Description & Meaning |
| :--- | :--- | :--- |
| `pending` | Active / Provisional | Authorized but unsettled movement (e.g., credit card pre-authorization, bank payment clearance in progress, or unconfirmed UPI transaction). Book balance is not yet impacted, but available balance reflects a temporary hold. |
| `posted` | Active / Settled | Fully cleared and settled transaction. The monetary amount has cleared the banking rail or settled in cash. The ledger book balance is updated and permanently immutable. |
| `failed` | Terminal | Settlement or bank clearing failed (e.g., insufficient funds, bank rail timeout, or merchant decline). Temporary holds on available balance are released. |
| `cancelled` | Terminal | The transaction was cancelled by the user or system prior to clearing. Only valid from the `pending` state. Holds are released immediately. |
| `reversed` | Terminal | A previously `posted` transaction that has been nullified by a formal compensating reversal transaction. The original record is retained forever for auditability. |

---

## 3. Transition Matrix & Invariants

The state machine strictly enforces the following transition rules in `backend/app/domain/transaction_types.py`:

```python
VALID_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
    TransactionStatus.PENDING: {
        TransactionStatus.POSTED,
        TransactionStatus.FAILED,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.POSTED: {
        TransactionStatus.REVERSED,
    },
    TransactionStatus.FAILED: set(),      # Terminal
    TransactionStatus.CANCELLED: set(),   # Terminal
    TransactionStatus.REVERSED: set(),    # Terminal
}
```

### 3.1 Transition Invariants
1. **No Direct Cancellation of Settled Funds:** Once a transaction transitions to `posted`, it cannot be `cancelled` or `deleted`. Attempting to cancel a `posted` transaction raises a `BusinessRuleViolationError: Cannot cancel a posted transaction; must use formal reversal`.
2. **Terminal State Immutability:** Transactions in `failed`, `cancelled`, or `reversed` status can never transition to any other state. Any update request attempting to modify their state or attributes is rejected.
3. **Immutability of Financial Attributes:** While in `posted` status, attributes affecting the financial ledger (`amount`, `amount_paise`, `currency`, `account_id`, `transaction_date`, `direction`) are locked against modification. Only non-financial metadata (`description`, `merchant_name`, `category_id`, `tags`, `metadata`) may be edited by authorized users.

---

## 4. Ledger & Balance Synchronization Per State

The application service (`TransactionService`) coordinates ledger balance adjustments on the parent `FinancialAccount` as transactions transition across lifecycle phases:

### 4.1 Transition: `intake` -> `pending`
- **Asset Account Outflow:** `available_balance_paise -= amount_paise`. `current_book_balance_paise` remains unchanged.
- **Asset Account Inflow:** No balance mutation until settled (avoids crediting unverified funds).
- **Liability Account:** Holds against credit limits are tracked without altering posted debt.

### 4.2 Transition: `pending` -> `posted`
- **Asset Account Outflow:** `current_book_balance_paise -= amount_paise`. Available balance hold is converted into a ledger deduction.
- **Asset Account Inflow:** `current_book_balance_paise += amount_paise`, `available_balance_paise += amount_paise`.
- **Liability Account Outflow (Purchase):** `outstanding_liability_paise += amount_paise`, `available_balance_paise -= amount_paise`.
- **Liability Account Inflow (Payment):** `outstanding_liability_paise -= amount_paise`, `available_balance_paise += amount_paise`.

### 4.3 Transition: `pending` -> `cancelled` or `failed`
- **Asset Account Outflow:** `available_balance_paise += amount_paise` (hold released back to user).
- **Book Balance:** Remains completely unaffected.

### 4.4 Transition: `posted` -> `reversed`
- The original transaction status is updated to `reversed`.
- A new companion transaction of type `adjustment` is inserted with opposite direction and `related_transaction_id` pointing to the original record.
- The balance mutation applied during the original posting is inverted with exact precision.

---

## 5. Domain Event Pipeline

Lifecycle state transitions dispatch domain events across the system to trigger notifications, budgeting recalculations, and audit logging:

| Event Name | Dispatched When | Payload Attributes |
| :--- | :--- | :--- |
| `transaction.posted` | Transaction settles or is directly created as `posted` | `transaction_id`, `workspace_id`, `account_id`, `amount_paise`, `direction`, `category_id`, `timestamp` |
| `transaction.cancelled` | Pending transaction is cancelled by user or workflow | `transaction_id`, `workspace_id`, `account_id`, `cancelled_by_id`, `timestamp` |
| `transaction.reversed` | Posted transaction undergoes compensating reversal | `transaction_id`, `workspace_id`, `reversal_transaction_id`, `reversal_reason`, `timestamp` |
| `transaction.refunded` | Partial or full refund is logged against a transaction | `original_transaction_id`, `refund_transaction_id`, `refund_amount_paise`, `workspace_id` |
| `transfer.created` | Paired internal transfer is executed across two accounts | `transfer_id`, `workspace_id`, `source_account_id`, `destination_account_id`, `amount_paise` |

Every event is recorded in the asynchronous events bus and processed within transactional outbox guarantees.
