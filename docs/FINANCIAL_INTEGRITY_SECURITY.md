# ARTHSAVORA — Financial Integrity & Fraud Resistance Standards

## 1. Executive Summary

Financial software must guarantee mathematical precision, immutability of historical records, idempotency of mutations, and balance integrity under concurrent transactions.

ARTHSAVORA enforces these guarantees through architectural constraints embedded in its double-entry ledger engine, transaction state machines, and concurrency locking mechanisms.

---

## 2. Core Financial Invariants

### 2.1. Exact Fixed-Point Arithmetic
- **Problem:** Standard floating-point types (`float`, `double`) introduce rounding errors that compound over millions of transactions (e.g., $0.1 + 0.2 \neq 0.3$).
- **Solution:** All monetary amounts are stored in PostgreSQL as `NUMERIC(18, 4)` and represented in domain code using Python's `Decimal` or integer sub-units (paise: ₹1 = 100 paise).
- **Verification:** Verified in `test_financial_amount_exact_precision`. Fractional amounts down to 4 decimal places are preserved exactly without drift.

### 2.2. Fundamental Accounting Invariant ($\sum \text{Debits} = \sum \text{Credits}$)
- **Rule:** A journal entry can never be posted unless the sum of its debit lines equals the sum of its credit lines down to the last decimal place.
- **Enforcement:** Enforced in `post_journal_entry` inside a single database transaction.
- **Verification:** Verified in `test_unbalanced_journal_post_rejected_with_exact_difference`. Any unbalanced entry raises `ValidationException` reporting the exact discrepancy:
  ```python
  if total_debits != total_credits:
      diff = abs(total_debits - total_credits)
      raise ValidationException(
          f"Unbalanced journal entry: Total Debits (₹{total_debits}) != Total Credits (₹{total_credits}). Difference: ₹{diff}"
      )
  ```

### 2.3. Immutability of Posted Records & Compensating Reversals
- **Rule:** Once a journal entry is posted, it transitions to `status = 'posted'` and becomes permanently immutable. Neither lines, amounts, accounts, nor descriptions can be edited or deleted.
- **Correction Protocol:** Corrections require creating and posting a formal **Reversal Entry** (`reverse_journal_entry`) that swaps debits and credits, references the original entry ID, and records the business reason and actor.
- **Verification:** Verified in `test_posted_journal_immutability_and_reversal`. Attempting to repost or delete a posted entry raises `ConflictException`.

### 2.4. Idempotency & Duplicate Prevention
- **Financial Replays:** Network timeouts or client retries can cause duplicate charges or ledger postings.
- **Idempotency Key:** Sensitive financial mutation endpoints accept an `Idempotency-Key` HTTP header. If a duplicate key is presented within the idempotency window, the server returns the cached initial response without re-executing the transaction.
- **Deduplication Hashing:** Bank statement imports and OCR uploads compute a SHA-256 fingerprint from `(account_id, transaction_date, amount, reference_number)` to detect and deduplicate recurring statement records automatically.

### 2.5. Concurrency Control & Row-Level Locking
- **Invoice & Account Balances:** When applying payments to business invoices or updating bank balances, the system applies PostgreSQL `SELECT ... FOR UPDATE` row locks.
- **Over-Allocation Prevention:** The payment allocation engine checks `applied_amount <= invoice.balance_due` under the active row lock, preventing race conditions from over-allocating invoice balances.

---

## 3. Fraud Resistance & Anomaly Principles

1. **OCR Output is Untrusted Data:** Extracted text from receipt images and PDF invoices is staged in a reviewable sandbox. The system never autonomously creates financial transactions or ledger entries from OCR output without explicit user confirmation.
2. **Objective Anomaly Classification:** Financial anomalies detected via statistical algorithms ($z$-score deviations, category spikes, unusual merchants) are presented as informational observations, never as definitive proof of fraud.
3. **No Autonomous Freezes:** The system never unilaterally freezes accounts or blocks user access based on AI anomaly scores.

---

## 4. Automated Verification Matrix

| Invariant | Test File | Test Case | Status |
| :--- | :--- | :--- | :--- |
| Exact Numeric Precision | `test_database.py` | `test_financial_amount_exact_precision` | **Passed** |
| Double-Entry Balance Check | `test_production_security_hardening.py` | `test_unbalanced_journal_post_rejected_with_exact_difference` | **Passed** |
| Posted Journal Immutability | `test_database.py` | `test_posted_journal_immutability_and_reversal` | **Passed** |
| Reversal Attribution | `test_database.py` | `test_posted_journal_immutability_and_reversal` | **Passed** |
| Deduplication Invariant | `test_import_and_data_acquisition.py` | `test_deduplication_engine` | **Passed** |
| Idempotency Cache | `test_idempotency.py` | `test_idempotent_post_replay` | **Passed** |
