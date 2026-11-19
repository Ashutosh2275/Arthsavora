# ARTHSAVORA Financial Data Reconciliation

## 1. Overview

Reconciliation is the formal process of comparing external bank-reported balances and transaction feeds against internal general ledger records to guarantee completeness, accuracy, and fraud prevention.

In ARTHSAVORA, automated reconciliation occurs immediately following every balance and transaction synchronization run.

---

## 2. Reconciliation Variance Calculation

The pure function `calculate_reconciliation_variance` in `app/domain/financial_connection.py` evaluates discrepancies:

$$\text{Variance} = \text{Reported Balance} - \text{Book Balance}$$

```python
def calculate_reconciliation_variance(
    provider_reported_balance_paise: int,
    calculated_book_balance_paise: int,
    unmatched_transactions_count: int = 0,
) -> ReconciliationVarianceVO:
    diff_paise = provider_reported_balance_paise - calculated_book_balance_paise
    diff_abs = abs(diff_paise)

    if diff_paise == 0 and unmatched_transactions_count == 0:
        status = ReconciliationStatus.MATCHED
        explanation = "Perfect reconciliation: External bank balance matches internal book balance."
    elif diff_abs > 1_000_000:  # > ₹10,000 variance
        status = ReconciliationStatus.CRITICAL_DISCREPANCY
        explanation = f"Critical discrepancy: Variance of ₹{diff_abs / 100:,.2f} between bank and book balance."
    else:
        status = ReconciliationStatus.VARIANCE_DETECTED
        explanation = f"Variance detected: External balance differs from book balance by ₹{diff_abs / 100:,.2f}."

    return ReconciliationVarianceVO(
        difference_paise=diff_paise,
        status=status,
        explanation=explanation,
        unmatched_count=unmatched_transactions_count,
    )
```

---

## 3. Reconciliation Records (`reconciliation_records`)

Each evaluation persists an auditable `ReconciliationRecord`:
- `reconciliation_date`: Calendar date of evaluation.
- `provider_reported_balance_paise`: Bank-reported amount.
- `calculated_book_balance_paise`: Internal ledger amount.
- `difference_paise`: Calculated variance.
- `status`: `matched`, `variance_detected`, `critical_discrepancy`, or `resolved`.
- `unmatched_transactions_count`: Number of external transactions not matched to receipts/invoices.
- `resolution_notes`: Documented explanation when a variance is investigated and marked resolved by a user.
- `resolved_at` & `resolved_by_id`: User attribution for audit compliance.

---

## 4. Discrepancy Root Causes & Resolution Workflows

Common sources of variance between bank and book balance:
1. **Timing Differences (Float)**:
   - Cheques issued but not yet presented at bank.
   - Weekend UPI settlements pending FIP ledger clearing.
   - *Resolution*: User marks variance as "Timing Difference" with automatic resolution once settlement clears.
2. **Unrecorded Bank Fees or Interest**:
   - Bank deducted quarterly SMS charges, annual card fees, or credited savings interest.
   - *Resolution*: User accepts automated one-click transaction creation to log the unrecorded fee.
3. **Manual Transaction Errors**:
   - An expense was manually entered twice or with incorrect minor units.
   - *Resolution*: User voids or edits the erroneous manual transaction.
4. **Fraudulent / Unauthorized Debits**:
   - Bank reports debits unknown to the account owner.
   - *Resolution*: Flagged immediately to user via high-priority notification (`NotificationSeverity.CRITICAL`).

---

## 5. Non-Destructive Invariant

> [!CAUTION]
> ARTHSAVORA will **never** automatically insert arbitrary "balancing adjustments" or overwrite historical general ledger entries to force a `matched` reconciliation status. Every balance variance must be explicitly accounted for through legitimate, auditable transactions.
