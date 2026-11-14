# ARTHSAVORA — IMPORT DEDUPLICATION SPECIFICATION

## 1. Deduplication Objectives

In accounting and personal finance, duplicate transaction records introduce severe errors: distorted balances, incorrect tax liabilities, false spending summaries, and corrupted double-entry general ledgers.

The Arthsavora statement deduplication engine enforces a 4-tier defense model:
1. **File Checksum Deduplication** (Prevents importing the same statement file twice).
2. **Exact Reference Deduplication** (Prevents re-importing transactions with matching bank reference numbers).
3. **Probable Envelope Deduplication** (Flags transactions matching date $\pm 1$ day, account, amount in paise, and direction).
4. **Intra-Batch Deduplication** (Flags repeated rows inside the same statement file).

---

## 2. Gate 1: Cryptographic File Checksum Matching

Before parsing an uploaded file:
1. Computes the SHA-256 hash of the incoming byte stream:
   $$\text{Checksum} = \text{SHA256}(\text{file\_bytes})$$
2. Queries `import_jobs` table:
   ```sql
   SELECT id, status, original_filename FROM import_jobs 
   WHERE workspace_id = :workspace_id 
     AND file_checksum = :checksum 
     AND status NOT IN ('failed', 'cancelled');
   ```
3. If an existing job is found and `allow_duplicate_file == False`, immediately aborts with `DuplicateImportError("This statement file was already uploaded on ...")`.

---

## 3. Gate 2: Exact Reference Matching

Bank statements consistently output unique tracking references: UTR numbers for NEFT/RTGS, UPI transaction reference numbers (12-digit IDs), cheque numbers, or IMPS reference codes.

1. When an incoming candidate has a non-empty `reference_number`:
   ```sql
   SELECT id, transaction_date, amount_paise, description FROM transactions
   WHERE workspace_id = :workspace_id
     AND account_id = :account_id
     AND (UPPER(external_transaction_id) = :ref_upper OR UPPER(source_reference) = :ref_upper)
     AND status IN ('posted', 'pending');
   ```
2. If matched:
   - Sets `candidate.duplicate_status = "exact"`
   - Sets `candidate.duplicate_match_id = existing_tx.id`
   - Sets `candidate.duplicate_reason = "Exact match with existing transaction #{id} (Ref: {ref})"`
   - Sets `candidate.selected_for_import = False`

---

## 4. Gate 3: Probable & Fuzzy Matching

When bank transactions lack unique reference numbers (e.g., cash withdrawals, ATM swipes, or POS merchant transactions):

1. The engine constructs a search envelope:
   $$\text{Candidate Date} - 1\text{ day} \le \text{Transaction Date} \le \text{Candidate Date} + 1\text{ day}$$
   $$\text{Transaction Amount Paise} == \text{Candidate Amount Paise}$$
   $$\text{Transaction Direction} == \text{Candidate Direction}$$
2. If matched:
   - Sets `candidate.duplicate_status = "probable"`
   - Sets `candidate.duplicate_match_id = existing_tx.id`
   - Sets `candidate.duplicate_reason = "Probable duplicate: matches existing transaction on YYYY-MM-DD for ₹X"`
   - Sets `candidate.selected_for_import = True` (flagged for review, but user can uncheck or confirm).

---

## 5. Gate 4: Intra-Batch Deduplication

Statement exports occasionally repeat identical records across page transitions or duplicate CSV rows.

1. As candidates are processed, the deduplicator maintains an in-memory dictionary of batch signatures:
   $$\text{Signature} = \text{Date} : \text{AmountPaise} : \text{Direction} : (\text{RefNo} \lor \text{Desc}_{[:20]})$$
2. If a signature has already been recorded in the current batch:
   - Sets `candidate.duplicate_status = "exact"`
   - Sets `candidate.duplicate_reason = "Identical transaction found earlier in this statement file (Row #{first_row})"`
   - Sets `candidate.selected_for_import = False`
   - Preserves candidate in the database so no rows are silently hidden from the user.

---

## 6. Review UI Presentation

In the Web Review Table:
- Exact duplicates feature a **red "Exact Duplicate" badge** and are unchecked by default.
- Probable duplicates feature an **amber "Probable Duplicate" badge** with a tooltip linking to the existing transaction.
- Non-duplicates feature a **green "None" badge**.
- Users retain absolute authority to toggle selection checkboxes before batch confirmation.
