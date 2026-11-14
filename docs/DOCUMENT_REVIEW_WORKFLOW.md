# Document Review Workflow & Explicit Human Confirmation Gate

## 1. Core Architectural Mandate

In institutional financial technology, **data provenance and transaction certainty** are paramount.

```
+-----------------------------------------------------------------------------------+
|                           PROBABILISTIC INTAKE DOMAIN                             |
|                                                                                   |
|  [Document Upload] ──> [Image Preprocessing] ──> [OCR] ──> [Extraction Heuristics]|
+-----------------------------------------┬-----------------------------------------+
                                          │ Unverified Suggestions (Read-Only)
                                          ▼
+-----------------------------------------------------------------------------------+
|                             HUMAN-IN-THE-LOOP GATE                                |
|                                                                                   |
|              [Side-by-Side Review] ──> [Inline Field Correction]                  |
|                                          │                                        |
|                          User Explicit Approval Required                          |
+-----------------------------------------┬-----------------------------------------+
                                          │ Verified Payload
                                          ▼
+-----------------------------------------------------------------------------------+
|                            DETERMINISTIC LEDGER DOMAIN                            |
|                                                                                   |
|  [Double-Entry General Ledger] <── [Immutable Journal Entry] <── [Account Balance] |
+-----------------------------------------------------------------------------------+
```

### The Inviolable Ledger Invariant
> **OCR extraction results are treated as untrusted draft suggestions.** Under no circumstances may an OCR extraction result independently write journal entries, debit an account balance, or register a financial transaction without explicit, authenticated human confirmation.

---

## 2. Document Lifecycle States

The document processing lifecycle tracks every stage from initial ingestion to final confirmation or rejection:

```
                  ┌─────────────────┐
                  │  PENDING_SCAN   │
                  └────────┬────────┘
                           │ Image Preprocessing & OCR
                           ▼
                  ┌─────────────────┐
                  │   PROCESSING    │
                  └────────┬────────┘
                           │ Field Extraction & Math Validation
                           ▼
                  ┌─────────────────┐
      ┌───────────┤    PROCESSED    ├───────────┐
      │           └────────┬────────┘           │
      │ User               │ User               │ User
      │ Corrects           │ Rejects            │ Confirms
      ▼                    ▼                    ▼
┌───────────┐     ┌─────────────────┐     ┌───────────┐
│ REVIEWED  │     │    REJECTED     │     │ CONFIRMED │
└─────┬─────┘     └─────────────────┘     └───────────┘
      │
      │ User Confirms
      ▼
┌───────────┐
│ CONFIRMED │
└───────────┘
```

| Lifecycle State | Description | Permitted Next Actions |
|---|---|---|
| `PENDING_SCAN` | File uploaded, stored, and queued for scanning | Process OCR |
| `PROCESSING` | Preprocessing or OCR actively executing | Await completion |
| `PROCESSED` | Extraction complete; waiting for human review | Review, Correct, Confirm, Reject |
| `REVIEWED` | Field corrections applied by user; ready for posting | Confirm, Reject, Additional Corrections |
| `CONFIRMED` | Transaction posted to ledger or linked to existing transaction | View, Download original file |
| `REJECTED` | Document dismissed as invalid, unreadable, or duplicate | View, Delete |

---

## 3. Side-by-Side Review Interface

The frontend Web application (`apps/web/src/pages/Documents.tsx`) implements an institutional side-by-side verification experience:

### 3.1 Visual Layout Structure
```
+-----------------------------------------------------------------------------------------------+
|  DOCUMENT REVIEW & CORRECTION                                         [x] Close Drawer        |
+---------------------------------------------------------------+-------------------------------+
|                                                               |  EXTRACTED FINANCIAL ENTITIES |
|                                                               |                               |
|                     ORIGINAL DOCUMENT VIEWER                  |  Merchant Name                |
|                                                               |  [ Swiggy Bangalore Central ] |
|                                                               |                               |
|  +---------------------------------------------------------+  |  Transaction Date   Amount    |
|  |                                                         |  |  [ 14/11/2026 ]  [ 550.00 ]   |
|  |             TAX INVOICE - SWIGGY                        |  |                               |
|  |             Order #12345678                             |  |  GSTIN (15 characters)        |
|  |                                                         |  |  [ 29AAACB7144P1Z9       ]   |
|  |  Items:                                                 |  |                               |
|  |  1. Paneer Tikka Biryani          Rs. 500.00            |  |  Subtotal      Taxes (CGST)   |
|  |                                                         |  |  [ 500.00 ]    [ 13.75 ]      |
|  |  Subtotal:                        Rs. 500.00            |  |                               |
|  |  CGST (2.5%):                     Rs.  13.75            |  |  Line Items Table             |
|  |  SGST (2.5%):                     Rs.  13.75            |  |  - Paneer Tikka (1x)  500.00  |
|  |  Packaging:                       Rs.  22.50            |  |                               |
|  |  TOTAL:                           Rs. 550.00            |  |  Account to Debit             |
|  |                                                         |  |  [ HDFC Bank (Savings)    v]  |
|  +---------------------------------------------------------+  |                               |
|                                                               |  Expense Category             |
|  [Zoom In] [Zoom Out] [Rotate] [Download]                     |  [ Food & Dining          v]  |
|                                                               |                               |
|                                                               |  [ Reject ]  [ Confirm & Post ]
+---------------------------------------------------------------+-------------------------------+
```

---

## 4. Field Correction Mechanics & Audit Trail

When a user modifies any extracted field, the system ensures a transparent and immutable record:

### 4.1 Correction Endpoint
- **HTTP**: `POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/correct`
- **Request Body**:
  ```json
  {
    "merchant_name": "Swiggy Bangalore Central",
    "total_amount": 550.00,
    "tax_amount": 27.50,
    "transaction_date": "2026-11-14",
    "notes": "Corrected merchant branch location"
  }
  ```

### 4.2 Immutable Audit Record (`document_reviews`)
Every review action creates a row in the `document_reviews` table capturing:
- `document_id`: The target document UUID.
- `reviewer_user_id`: The authenticated operator performing the review.
- `review_action`: `"corrected"`, `"confirmed"`, or `"rejected"`.
- `field_diffs`: JSON structure logging `{ "before": {...}, "after": {...} }`.
- `notes`: User-provided justification or notes.

A new `DocumentExtractionResult` record is generated with updated fields and `is_user_reviewed = True`, preserving the original raw OCR extraction for algorithm evaluation and auditability.

---

## 5. Confirmation Gate & Transaction Ingestion

When the user clicks **Confirm & Post Transaction**, the system executes the following deterministic sequence:

1. **Permission Check**: Verifies the user possesses `Permission.MANAGE_DOCUMENTS` in the target workspace.
2. **Account Validation**: Validates that the selected `account_id` exists in the workspace and is an active financial account.
3. **Transaction Creation**:
   - Calls `TransactionService.intake_transaction` with:
     - `amount_paise`: Exact integer minor units.
     - `transaction_date`: Extracted/corrected date.
     - `description`: Document merchant and receipt reference.
     - `transaction_type`: `DEBIT` (Expense).
     - `category_id`: Assigned expense category.
4. **General Ledger Posting**: The transaction service updates the double-entry accounting ledger and account balances atomically.
5. **Association Creation**: Inserts a `DocumentTransactionAssociation` row, establishing a bidirectional link between the document and the authoritative transaction ID.
6. **Status Transition**: Updates `FinancialDocument.status` to `DocumentStatus.CONFIRMED`.

---

## 6. Linking to Existing Transactions

In many workflows, the transaction already exists in the workspace (for example, imported via net banking or credit card statements prior to scanning the physical slip).

To prevent duplicate expenses:
1. The **Transaction Matcher** scans existing transactions and presents candidate matches in the review drawer.
2. The user can click **Link to Existing Transaction**.
3. **Endpoint**: `POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/link/{transaction_id}`.
4. This creates a `DocumentTransactionAssociation` linking the receipt proof directly to the existing transaction record without creating a duplicate expense.

---

## 7. Related Documentation

- [Receipt Intelligence Architecture](file:///d:/Arthsavora/docs/RECEIPT_INTELLIGENCE_ARCHITECTURE.md)
- [Receipt Transaction Matching](file:///d:/Arthsavora/docs/RECEIPT_TRANSACTION_MATCHING.md)
- [Transaction Architecture](file:///d:/Arthsavora/docs/TRANSACTION_ARCHITECTURE.md)
- [Double-Entry Accounting Architecture](file:///d:/Arthsavora/docs/ACCOUNTING_ARCHITECTURE.md)
