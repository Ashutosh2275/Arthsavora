# Receipt & Document Transaction Matching Architecture

## 1. Overview & Objective

A common scenario in commercial and personal financial management is the delayed scanning of paper receipts. Users frequently scan receipts days after the financial transaction was recorded via bank statement import, net banking feeds, or manual entry.

If every scanned receipt automatically generated a new transaction, the user's ledger would suffer from **duplicate expenses** and distorted financial analytics.

The **Receipt Transaction Matcher** implemented in [matcher.py](file:///d:/Arthsavora/backend/app/services/document/matcher.py) performs an intelligent correlation scan across existing workspace transactions, identifying matching candidates and allowing users to link receipt documentation directly to authoritative records.

---

## 2. Correlation Scan Algorithm

```
Extracted Receipt Entity
(Total: ₹550.00, Date: 14/11/2026, Merchant: "Swiggy")
                       │
                       ▼
   [Query Workspace Transactions within Date Window]
              (Date: 09/11/2026 to 19/11/2026)
                       │
                       ▼
        [Iterate Candidate Transactions]
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
  [Amount Check]                [Date Delta]
(Exact paise match?)          (Days difference?)
        │                             │
        └──────────────┬──────────────┘
                       │
                       ▼
        [Merchant & Description Scoring]
         (Levenshtein / Token Overlap)
                       │
                       ▼
         [Calculate Composite Score]
                       │
                       ▼
    [Classify Match Status & Emit Candidates]
```

### 2.1 Date Window Parameters
Credit card charges, POS terminal batches, and UPI merchant settlements often exhibit a 1 to 3 day settlement lag before reflecting on bank statements.
- **Default Search Window**: `+/- 5 calendar days` around the extracted receipt date.
- **Date Penalty**:
  - `0 days delta` (Same day): 1.00 multiplier.
  - `1-2 days delta`: 0.90 multiplier.
  - `3-5 days delta`: 0.75 multiplier.

### 2.2 Amount Matching
Because monetary amounts are compared as 64-bit integers (`paise`), comparison is exact and immune to floating-point imprecision:
- **Exact Match (`diff == 0 paise`)**: Base score of 0.80.
- **Close Match (`diff <= 100 paise`)**: Base score of 0.60 (handling possible cash round-off).
- **Mismatched Amount (`diff > 100 paise`)**: Disqualified from candidate pool unless explicit override applies.

### 2.3 Merchant Text Similarity
The matcher compares the extracted merchant name with the candidate transaction's `description` field:
- Normalizes both strings (lowercasing, punctuation stripping, stopword removal).
- Computes token overlap and subsequence similarity.
- Adds up to +0.20 to the composite score for strong merchant name correlation.

---

## 3. Match Status Taxonomy

The matcher categorizes the correlation result into four distinct classifications:

| Match Status | Threshold Criteria | Recommended Action |
|---|---|---|
| **EXACT** | Single candidate with `score >= 0.90` (Exact amount, same day, matching merchant) | Highlight candidate; offer single-click "Link to Existing" |
| **CANDIDATE** | 1 or 2 candidates with `0.70 <= score < 0.90` (Amount matches, date within window) | Present candidate list with score breakdown for selection |
| **AMBIGUOUS** | Multiple candidates with near-identical scores (e.g. repeated ₹500 transactions) | Alert user to multiple potential matches; require careful selection |
| **NONE** | No matching transactions found within amount/date criteria | Default to "Create & Post New Transaction" |

---

## 4. Scored Candidate Representation

When candidates are detected, the matcher emits structured DTOs containing complete correlation evidence:

```json
{
  "match_status": "EXACT",
  "candidates": [
    {
      "transaction_id": "8fa134d2-3c22-48a5-8ea1-42775f0a0912",
      "transaction_date": "2026-11-14",
      "amount_paise": 55000,
      "description": "SWIGGY BANGALORE IN",
      "account_name": "HDFC Bank Savings",
      "match_score": 0.95,
      "reasons": [
        "Exact amount match (55000 paise)",
        "Same day transaction (0 days delta)",
        "Strong merchant name match"
      ]
    }
  ]
}
```

---

## 5. Bidirectional Association Data Model

When a user links a receipt to an existing transaction, the system records the association in `document_transaction_associations`:

```sql
CREATE TABLE document_transaction_associations (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES financial_documents(id) ON DELETE CASCADE,
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    association_type VARCHAR(32) NOT NULL DEFAULT 'PROOF',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_doc_tx_assoc UNIQUE (document_id, transaction_id)
);
```

### 5.1 Benefits of Bidirectional Querying
1. **Document-Centric View**: Users viewing a receipt document can inspect the authoritative ledger transaction, debit account, and journal entry.
2. **Transaction-Centric View**: Users viewing a transaction on the ledger or bank statement can click **View Attached Receipts** to open the scanned receipt preview and verify line-item expenses.
3. **Audit Readiness**: Tax auditors and Chartered Accountants (CAs) can inspect verified document proofs directly from the general ledger.

---

## 6. Linking & Unlinking API Endpoints

- **Link Receipt to Transaction**:
  `POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/link/{transaction_id}`
  - Validates both entities belong to the workspace.
  - Inserts `DocumentTransactionAssociation`.
  - Sets document status to `DocumentStatus.CONFIRMED`.

- **Unlink Receipt from Transaction**:
  `DELETE /api/v1/workspaces/{workspace_id}/documents/{document_id}/link/{transaction_id}`
  - Deletes `DocumentTransactionAssociation`.
  - Returns document status to `DocumentStatus.REVIEWED` if no other associations exist.

---

## 7. Related Documentation

- [Receipt Intelligence Architecture](file:///d:/Arthsavora/docs/RECEIPT_INTELLIGENCE_ARCHITECTURE.md)
- [Document Review Workflow](file:///d:/Arthsavora/docs/DOCUMENT_REVIEW_WORKFLOW.md)
- [Transaction Architecture](file:///d:/Arthsavora/docs/TRANSACTION_ARCHITECTURE.md)
- [Double-Entry Accounting Architecture](file:///d:/Arthsavora/docs/ACCOUNTING_ARCHITECTURE.md)
