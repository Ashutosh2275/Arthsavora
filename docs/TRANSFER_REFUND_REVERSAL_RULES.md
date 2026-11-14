# Arthsavora — Paired Transfers, Cumulative Refunds & Compensating Reversals

## 1. Overview & Financial Integrity Guarantees

Financial ledger accuracy requires precise conventions for multi-account money movement, merchant refunds, and transaction corrections. 

In Arthsavora, transfers, refunds, and reversals are engineered as first-class domain concepts with strict mathematical invariants to prevent double-counting, balance leaks, and orphaned records.

---

## 2. Paired Account Transfers

### 2.1 The Double-Leg Pattern
An internal transfer represents money moving from one account to another within the same workspace (e.g., transferring INR 25,000 from an HDFC Savings Account to an ICICI Current Account, or paying a Credit Card bill).

To maintain double-entry integrity and independent statement reconciliation, every transfer is recorded as **two distinct but atomically linked transaction records**:
1. **Source Leg (`transfer_out`):** Direction `outflow`. Decreases the source account balance.
2. **Destination Leg (`transfer_in`):** Direction `inflow`. Increases the destination account balance.

```
+-----------------------------------------------------------------------------------------+
|                                    Transfer Operation                                   |
|                               (Shared transfer_id: UUID)                                |
+--------------------------------------------+--------------------------------------------+
                                             |
                     +-----------------------+-----------------------+
                     |                                               |
                     v                                               v
       +----------------------------+                 +----------------------------+
       |   Outbound Leg             |                 |   Inbound Leg              |
       |   Type: transfer_out       |                 |   Type: transfer_in        |
       |   Direction: outflow       |                 |   Direction: inflow        |
       |   Account: Source Account  |                 |   Account: Target Account  |
       |   Amount: ₹25,000.00       |                 |   Amount: ₹25,000.00       |
       |   related_id: -> Inbound   |                 |   related_id: -> Outbound  |
       +----------------------------+                 +----------------------------+
```

### 2.2 Transfer Invariants
- **Atomic Execution:** Both transaction legs and their corresponding account balance updates are executed inside a single PostgreSQL database transaction. If either leg fails validation, the entire operation is rolled back.
- **Shared Correlation Identifier (`transfer_id`):** A unique UUID is generated prior to persistence and assigned to both transaction records, enabling single-query lookup of the entire transfer pair.
- **Cross-Referenced Relationship:** Each leg sets `related_transaction_id` pointing directly to the primary key (`id`) of its counterpart leg.
- **Workspace Confinement:** Both accounts must belong to the exact same workspace. Cross-workspace transfers are strictly prohibited to prevent data leakage and cross-entity pollution.
- **Identical Denomination:** Both accounts must share the same currency code (e.g., INR). Cross-currency transfers require explicit foreign exchange conversion metadata.

### 2.3 Credit Card Bill Payment Semantics
A common mistake in personal finance applications is classifying credit card bill payments as "Expenses". Doing so causes **double-counting**:
- The user already incurred an expense when purchasing groceries or electronics with the credit card.
- Paying the credit card statement merely settles an existing liability with cash assets.

In Arthsavora, credit card bill payments are modeled as **transfers**:
1. Outbound leg on the Bank Account: Decreases `current_book_balance_paise`.
2. Inbound leg on the Credit Card Account: Decreases `outstanding_liability_paise` and increases `available_balance_paise` (restoring available credit limit).
3. **Net Worth Impact:** Zero net change in workspace net worth, correctly reflecting debt discharge without inflating monthly expense metrics.

---

## 3. Cumulative Refund Subsystem

When a merchant reimburses a previously incurred expenditure (e.g., an e-commerce return, flight cancellation, or overbilling adjustment), the transaction engine records a linked refund.

### 3.1 The Refund Pattern
- **Transaction Type:** `refund`.
- **Direction:** `inflow` (reimburses the asset account).
- **Parent Linkage:** `related_transaction_id` stores the UUID of the original `outflow` transaction.

### 3.2 Mathematical Bounding Invariant
The engine enforces that the total sum of all refunds issued against a transaction can never exceed the original transaction's posted amount:

$$\sum_{k=1}^{n} \text{refund\_amount\_paise}_k \le \text{original\_transaction.amount\_paise}$$

```python
# Validation logic in TransactionService:
cumulative_refunds_paise = await self.transaction_repo.get_cumulative_refund_amount(
    workspace_id=workspace_id,
    original_transaction_id=original_tx.id
)

if cumulative_refunds_paise + refund_amount_paise > original_tx.amount_paise:
    raise BusinessRuleViolationError(
        f"Cumulative refunds ({cumulative_refunds_paise + refund_amount_paise} paise) "
        f"exceed original transaction amount ({original_tx.amount_paise} paise)",
        rule_name="MAX_REFUND_EXCEEDED"
    )
```

### 3.3 Partial & Staggered Refunds
A user or merchant may issue multiple partial refunds (e.g., returning two items from a single multi-item order on different dates). The engine permits successive partial refunds as long as the cumulative ceiling is not breached.

---

## 4. Compensating Reversals

### 4.1 Immutability of Posted Financial Facts
In production financial systems, records that have affected account balances must never be deleted using raw SQL `DELETE`. Deleting posted transactions causes audit gaps, breaks balance reconciliation, and prevents regulatory auditing.

Instead, Arthsavora implements **formal compensating reversals**:
1. The status of the original posted transaction transitions to `reversed`.
2. The user or system must supply a mandatory, auditable `reversal_reason`.
3. A new compensating transaction of type `adjustment` is inserted into the ledger with the opposite direction and `related_transaction_id` pointing to the original record.
4. The exact balance mutation previously applied is inverted on the parent `FinancialAccount`.

### 4.2 Reversal Workflow & Event Dispatch
```
[User / Admin] 
       | 
       v  POST /transactions/{id}/reverse (with reversal_reason)
[TransactionService]
       |
       +--> 1. Verify original_tx.status == 'posted'
       |
       +--> 2. Transition original_tx.status = 'reversed', record reversal_reason
       |
       +--> 3. Insert compensating transaction (type='adjustment', inverted direction)
       |
       +--> 4. Invert account balance impact on FinancialAccount
       |
       +--> 5. Commit atomic database transaction
       |
       +--> 6. Dispatch domain event: transaction.reversed
```

This ensures complete audit transparency: both the erroneous transaction and its compensating adjustment remain visible on the ledger, preserving historical accuracy.
