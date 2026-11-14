# Arthsavora — Transaction Matching & Reconciliation Rules

## 1. Scope & Objective

When actual financial transactions are imported or posted, Arthsavora attempts to reconcile them with expected recurring occurrences. Reconciling an occurrence links reality to expectation without altering accounting books or distorting cash balances.

---

## 2. Matching Criteria & Scoring Dimensions

The domain engine evaluates candidate matches using four deterministic scoring dimensions:

| Dimension | Window / Range | Maximum Points | Logic |
|---|---|---|---|
| **Date Proximity** | $\pm 5$ days | 40 points | 40 pts for exact date; decay linearly by 6 pts per day difference up to 5 days. |
| **Amount Match** | Exact or within 10% | 40 points | 40 pts for exact `paise`; 20 pts if within 5%; 10 pts if within 10%. |
| **Merchant Match** | Exact `merchant_id` or string | 15 points | 15 pts if IDs match or merchant name matches normalized description. |
| **Account Match** | Exact `account_id` | 5 points | 5 pts if bank/card account matches expected source account. |

Total Confidence Score ranges from $0$ to $100$.
- **High Confidence ($\ge 80$)**: Eligible for auto-reconciliation or one-click suggested match.
- **Medium Confidence ($60 - 79$)**: Surfaced in the UI for user review.
- **Low Confidence ($< 60$)**: Excluded from suggestions to eliminate noise.

---

## 3. Reconciliation State Invariants

1. **One-to-One Association**:
   - An occurrence can match at most one posted transaction (`matched_transaction_id`).
   - A single transaction can only be matched to one recurring occurrence. Relational index and validation logic enforce unique matching.

2. **Amount Variance Recording**:
   - For utility bills and variable subscriptions (e.g. AWS or electricity), actual amount rarely equals expected amount.
   - When matched:
     $$\text{amount\_variance\_paise} = \text{matched\_amount\_paise} - \text{expected\_amount\_paise}$$
   - The original `expected_amount_paise` is preserved on the occurrence for variance analysis.

3. **Reversibility**:
   - Users can unmatch an occurrence at any time.
   - Unmatching clears `matched_transaction_id`, resets status back to `due` or `overdue`, and records the audit event.
   - The posted transaction itself remains completely unaffected in the General Ledger.
