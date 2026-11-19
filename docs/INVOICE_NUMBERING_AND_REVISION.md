# Invoice Numbering, Revision & Cancellation Architecture

## 1. Sequential Invoice Numbering

In accordance with Indian tax practices and commercial bookkeeping standards, invoice numbers must be sequential, predictable, and unique within each workspace.

### Pattern:
`<PREFIX>-<YEAR>-<4-DIGIT-SEQUENCE>`
Examples:
- `INV-2026-0001`
- `INV-2026-0042`
- `ROY-2026-0105`

### Database Concurrency & Uniqueness:
- Invoice sequence generation uses `SELECT COUNT(*) + 1` scoped to `(workspace_id, fiscal_year, prefix)` within an isolated database transaction.
- A database-level unique constraint `uq_workspace_invoice_number` on `(workspace_id, invoice_number)` guarantees that parallel invoice creations cannot produce duplicate numbering.
- Users may optionally specify a custom invoice number during creation, subject to the same workspace uniqueness constraint.

---

## 2. Immutability & Snapshots

When an invoice transitions from `draft` to `issued`:
1. The invoice's state is locked.
2. A complete snapshot is generated and stored in `issued_snapshot` (JSONB).
3. The snapshot encapsulates:
   - Business profile (name, address, GSTIN, PAN).
   - Client profile (name, billing address, GSTIN, PAN).
   - All line items (descriptions, HSN/SAC, quantities, unit prices, discounts, tax rates, CGST/SGST/IGST breakdown).
   - Totals (subtotal, taxes, grand total).
   - Terms and bank payment details.
4. Subsequent edits to client master data or business profile never alter the issued invoice snapshot.

---

## 3. Controlled Invoice Cancellation

Invoices with issued status cannot be arbitrarily deleted. If an invoice was created in error or cancelled by client agreement:
- `cancel_invoice()` must be called with an explicit human-authored cancellation reason.
- Status is updated to `cancelled` and timestamped with `cancelled_at`.
- An automatic reversal journal entry is posted to the General Ledger, debiting revenue (`4020`) and crediting accounts receivable (`1040`), bringing net receivables back to balance.
