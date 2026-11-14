# Arthsavora — Transaction Deduplication & Idempotency Strategy

## 1. The Deduplication Challenge in Fintech

In modern financial management platforms, transactions arrive from multiple disparate channels:
- Direct user manual entry (web, PWA, mobile).
- Periodic CSV/OFX statement uploads from retail banks.
- Bank account aggregators (Setu, Finvu, OneMoney) with automated webhook retries.
- Client-side Android/iOS SMS parsing engines re-scanning notification histories.
- Unreliable network connections causing mobile clients to retry requests when timeouts occur.

Without deterministic deduplication and idempotency controls, duplicate entries proliferate, distorting account balances, skewing net worth, and corrupting tax calculations.

---

## 2. Multi-Layer Deduplication Architecture

Arthsavora enforces a defense-in-depth deduplication framework across three distinct architectural layers:

```
+-----------------------------------------------------------------------------------------+
|                                Incoming Transaction Request                             |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
| Layer 1: HTTP API Idempotency Key Verification                                          |
| Check header 'Idempotency-Key' against `ix_transactions_idempotency`                    |
| -> If match found: return existing transaction immediately (Idempotent 200 OK)         |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
| Layer 2: External Reference Unique Constraint Verification                             |
| Check `(workspace_id, source_type, external_reference)` in database                     |
| -> If collision occurs: raise 409 Conflict with `DUPLICATE_TRANSACTION` code            |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
| Layer 3: Fuzzy / Content Fingerprinting (Bank Feeds & CSV Imports)                      |
| Compute SHA-256 hash over account, date window, amount_paise, and normalized payee      |
| -> Flag suspected duplicate for user confirmation during bulk reconciliation            |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Layer 1: API Idempotency Keys

For programmatic API mutations and mobile app sync operations, clients provide a unique client-generated UUID in the `Idempotency-Key` HTTP header.

### 3.1 Idempotency Table Index
```sql
CREATE INDEX ix_transactions_idempotency 
ON transactions(workspace_id, idempotency_key) 
WHERE idempotency_key IS NOT NULL;
```

### 3.2 Idempotency Contract
1. **First Request:** The transaction is processed, inserted into the database with `idempotency_key = <client_key>`, and returns `201 Created`.
2. **Subsequent Request with Same Key:** The repository detects the existing record matching `workspace_id` and `idempotency_key`. The service returns the identical transaction response without creating a secondary ledger entry or re-mutating account balances.

---

## 4. Layer 2: External Reference Constraints

Financial institutions, payment gateways (Razorpay, Stripe), and Account Aggregator networks assign persistent reference IDs to transactions (e.g., Bank RRN, UTR number, or UPI transaction ID).

### 4.1 Database Partial Unique Index
Arthsavora enforces global uniqueness within each workspace per source type using a partial unique index:

```sql
CREATE UNIQUE INDEX uq_workspace_external_tx 
ON transactions(workspace_id, source_type, external_reference) 
WHERE external_reference IS NOT NULL;
```

### 4.2 Behavior on Collision
If an ingestion job attempts to re-import a transaction with an identical `external_reference` under the same `source_type`:
- PostgreSQL rejects the insert with an integrity violation (`UniqueViolation`).
- The repository intercepts the error and raises a `DuplicateTransactionError`.
- The API responds with `409 Conflict`:
```json
{
  "detail": {
    "code": "DUPLICATE_TRANSACTION",
    "message": "A transaction with this external reference already exists in this workspace",
    "existing_transaction_id": "c1f7a8b4-9e32-4d51-87ab-893cf1a02931"
  }
}
```

---

## 5. Layer 3: Content Fingerprinting for Statement Feeds

For legacy bank CSV files or SMS alerts lacking global reference IDs, the ingestion pipeline generates a deterministic SHA-256 fingerprint:

$$\text{Fingerprint} = \text{SHA256}(\text{account\_id} \parallel \text{transaction\_date\_iso} \parallel \text{amount\_paise} \parallel \text{direction} \parallel \text{normalized\_description})$$

### 5.1 Normalization Rules
1. **Description Trimming:** Removes whitespace, punctuation, and dynamic transaction noise (e.g., trailing timestamp strings, terminal branch codes).
2. **Case Normalization:** Converts merchant and description strings to lowercase.
3. **Paise Precision:** Uses exact integer `amount_paise` to avoid float formatting mismatches.

### 5.2 Storage in Provenance Metadata
The calculated fingerprint is stored in `source_provenance["content_hash"]`. During batch ingestion, rows matching an existing fingerprint within a $\pm 48\text{-hour}$ window are flagged as potential duplicates, prompting user review before ledger posting.
