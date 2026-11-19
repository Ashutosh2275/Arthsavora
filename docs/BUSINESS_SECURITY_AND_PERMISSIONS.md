# ARTHSAVORA — BUSINESS SECURITY, PERMISSIONS AND ACCESS CONTROL

## 1. Executive Summary

Small business financial management within Arthsavora involves sensitive commercial transactions, statutory registrations (GSTIN, PAN), billing artifacts, client/vendor directories, and authoritative general ledger postings. 

This document defines the architectural security framework governing:
1. **Multi-Tenant Workspace Isolation** and Row-Level Security (RLS).
2. **Insecure Direct Object Reference (IDOR) Defenses**.
3. **Role-Based Access Control (RBAC)** across small business roles.
4. **Data Integrity & Immutability Rules** (Issued Invoice Snapshots & Journal Reversals).
5. **Formula Injection Sanitization (CWE-1236)** on CSV exports.
6. **Audit Logging & Activity Trails**.

---

## 2. Multi-Tenant Isolation & Tenancy Scoping

### 2.1 Principle of Absolute Tenant Partitioning
In Arthsavora, every commercial entity (`BusinessProfile`, `BusinessClient`, `BusinessVendor`, `BusinessInvoice`, `BusinessPayable`, `BusinessActivity`) is strictly scoped by `workspace_id`. Cross-workspace visibility, queries, or foreign key joins are prohibited.

```sql
-- Every entity schema enforces workspace foreign keys with cascading safety
workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE
```

### 2.2 Repository Tenancy Enforcement
In `BusinessRepository`, every database query unconditionally applies the `workspace_id` filter:
```python
stmt = (
    select(BusinessInvoice)
    .where(
        BusinessInvoice.workspace_id == workspace_id,
        BusinessInvoice.id == invoice_id
    )
)
```
Even when an ID is directly provided by the caller, queries never search by entity primary key alone.

---

## 3. IDOR (Insecure Direct Object Reference) Defenses

### 3.1 Defense-in-Depth Verification
When performing business operations involving referenced resources (such as attaching a client to an invoice, linking a bank account for payment, or recording a bill against a vendor), the system enforces two layers of IDOR defense:

1. **Workspace Context Resolution:** The API route extracts the authenticated user's active `workspace_id` from the verified session/JWT and resolves membership permissions via `require_permission`.
2. **Referenced Entity Verification:** Before persisting associations, the service verifies that all foreign entities belong to the identical `workspace_id`:
   - `client.workspace_id == context.workspace_id`
   - `vendor.workspace_id == context.workspace_id`
   - `account.workspace_id == context.workspace_id`
   - `invoice.workspace_id == context.workspace_id`

If any entity belongs to another tenant or does not exist, the repository returns `None` and the service raises `NotFoundException("Resource not found")` without leaking cross-tenant existence.

---

## 4. Role-Based Access Control (RBAC) Matrix

Business workspaces support specialized commercial and accounting personas:
- **`owner`**: Complete operational, legal, and financial authority.
- **`admin`**: Operational business management and configuration.
- **`accountant`**: Financial accounting, journal ledger operations, invoice/payable lifecycle management.
- **`approver`**: Operational invoice and bill verification, client and vendor approvals.
- **`staff`**: Front-office invoicing and client operations.
- **`viewer`**: Read-only stakeholder and auditor visibility.

### 4.1 Granular Business Permissions

| Permission | Identifier | Purpose |
| :--- | :--- | :--- |
| `VIEW_BUSINESS_FINANCE` | `business:view_finance` | View business profile, summaries, aging charts, and cash-flow reports |
| `MANAGE_BUSINESS_FINANCE` | `business:manage_finance` | Update business profile, statutory tax settings (GSTIN, PAN), and business defaults |
| `MANAGE_INVOICES` | `business:manage_invoices` | Draft, issue, cancel, and record customer payments on invoices |
| `MANAGE_CLIENTS` | `business:manage_clients` | Create, update, and manage client profiles |
| `MANAGE_VENDORS` | `business:manage_vendors` | Create, update, and manage vendor profiles |
| `MANAGE_PAYABLES` | `business:manage_payables` | Record vendor bills, schedule disbursements, and record bill payments |

### 4.2 Role-to-Permission Mapping in Business Workspaces

| Permission | Owner | Admin | Accountant | Approver | Staff | Viewer |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `VIEW_BUSINESS_FINANCE` | Yes | Yes | Yes | Yes | Yes | Yes |
| `MANAGE_BUSINESS_FINANCE` | Yes | Yes | Yes | No | No | No |
| `MANAGE_INVOICES` | Yes | Yes | Yes | Yes | Yes | No |
| `MANAGE_CLIENTS` | Yes | Yes | Yes | Yes | Yes | No |
| `MANAGE_VENDORS` | Yes | Yes | Yes | Yes | No | No |
| `MANAGE_PAYABLES` | Yes | Yes | Yes | Yes | No | No |

---

## 5. Data Immutability & Financial Audit Safety

### 5.1 Issued Invoice Immutability
Once an invoice transitions from `DRAFT` to `ISSUED`:
1. **Issued Snapshot:** The exact state of the invoice—including buyer/seller names, tax identification, addresses, line items, rates, taxes, and total amounts—is serialized into an immutable JSONB column `issued_snapshot`.
2. **Locking:** Line items, totals, client links, and invoice numbers cannot be edited or deleted.
3. **General Ledger Posting:** An authoritative double-entry journal entry is immutably posted to the general ledger (Debit 1040 Accounts Receivable, Credit 4020 Service Revenue).

### 5.2 Controlled Invoice Cancellation
Invoices are legal documents and cannot be hard-deleted once issued:
- The status is set to `CANCELLED`.
- A reversing journal entry is automatically posted to the General Ledger via `LedgerService.reverse_journal()` to zero out receivables and recognized revenue.
- Cancellation reasons are recorded in the audit trail.
- Invoices with recorded payments cannot be cancelled unless payments are explicitly refunded or unallocated first.

---

## 6. Formula Injection (CWE-1236) Defense

Exporting financial registers (invoice and bill registers) to CSV creates risk of CSV/Formula Injection if user-supplied client names, invoice numbers, or descriptions begin with formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`).

All cell contents in `BusinessService.export_invoices_csv()` and `export_payables_csv()` are passed through `sanitize_csv_cell()`:

```python
def sanitize_csv_cell(value: Any) -> str:
    """Neutralize spreadsheet formula injection by prefixing risky characters with a single quote."""
    if value is None:
        return ""
    str_val = str(value).strip()
    if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{str_val}"
    return str_val
```

---

## 7. Audit Activity Trail

Every business-critical mutation automatically creates an immutable `BusinessActivity` record:
- **Actor:** `actor_id` (User UUID).
- **Tenant:** `workspace_id`.
- **Entity Reference:** `entity_type` (`invoice`, `payable`, `client`, `vendor`) and `entity_id`.
- **Action Type:** `created`, `issued`, `payment_recorded`, `cancelled`, `bill_recorded`, etc.
- **Metadata:** Key deltas, amounts, and notes stored in JSONB format.
- **Timestamp:** Server-authoritative UTC `created_at`.

These audit logs are accessible via `/api/v1/business/activities` for compliance, internal controls, and forensic analysis.
