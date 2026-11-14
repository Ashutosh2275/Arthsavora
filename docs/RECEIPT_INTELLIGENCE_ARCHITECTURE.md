# Receipt Intelligence & Document Extraction Architecture

## 1. System Overview

Arthsavora's Document Intelligence and Receipt Processing Engine enables automated, high-fidelity financial data ingestion from physical receipts, digital images (JPEG, PNG, WebP), and vector PDF invoices. Designed with an **India-first** foundation, the engine extracts Indian tax entities (GSTIN, CGST, SGST, IGST), recognizes merchant counterparties, parses itemized lines, and assigns granular confidence vectors.

### Core Architectural Principle
> **OCR output is strictly untrusted data.** It represents automated textual and numeric suggestions extracted from unstructured media. Optical character recognition data **must never silently post to the authoritative general ledger or alter financial balances without explicit human review and confirmation.**

```
+-----------------------------------------------------------------------------------+
|                            Uploaded Document (Image / PDF)                        |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
                     [Magic-Byte & Format Validation Engine]
                                         │
                                         ▼
                     [Secure Storage & SHA-256 Deduplication]
                                         │
                                         ▼
                     [Non-Destructive Image Preprocessing]
                     (EXIF, Grayscale, Contrast, Noise Filter)
                                         │
                                         ▼
                        [OCR Provider Abstraction Layer]
                   (Tesseract / Native PDF / Mock Test Engine)
                                         │
                                         ▼
                       [India-First Entity Field Extractor]
                 (Merchant, GSTIN, Date, Taxes, Total, Line Items)
                                         │
                                         ▼
                      [Mathematical Validation & Confidence]
                   (Subtotal + Tax - Discount == Total Amount)
                                         │
                                         ▼
                      [Merchant & Category Intelligence]
                                         │
                                         ▼
                     [Transaction Matcher (Correlation Scan)]
                                         │
                                         ▼
                    [User Side-by-Side Review & Correction]
                                         │
                                         ▼
            [Explicit Confirmation Gate -> Authoritative Ledger Mutation]
```

---

## 2. Component Architecture

### 2.1 File Ingestion & Security Isolation
- **Endpoint**: `POST /api/v1/workspaces/{workspace_id}/documents/upload`
- **Validation**:
  - Magic-byte verification (`%PDF-`, `\xFF\xD8\xFF`, `\x89PNG\r\n\x1a\n`, `RIFF...WEBP`).
  - Size limitation strictly enforced at 15 MB (`MAX_DOCUMENT_SIZE_BYTES`).
  - Cryptographic integrity check: SHA-256 hash computed on ingress to deduplicate and prevent duplicate uploads.
- **Tenant Isolation**: Files are partitioned under `storage/documents/{workspace_id}/{document_id}/` using sanitized path components.

### 2.2 OCR Engine Abstraction
The system utilizes a modular, provider-independent abstraction (`BaseOCREngine`):
- `TesseractOCREngine`: Open-source OCR for raster image scanning with word-level confidence evaluation.
- `PdfTextExtractor`: Native vector PDF parser extracting embedded text with near-instantaneous execution.
- `MockDeterministicOCREngine`: Deterministic test engine emitting reproducible Indian receipt text templates (Swiggy, Reliance Fresh, Petrol Pump, Cafe Coffee Day) for CI/CD pipelines.

### 2.3 Extraction & Validation Engine
- **Field Extractor**: Rule-based regex and contextual table line parsing.
- **Arithmetic Validator**: Reconciles `subtotal + tax - discount == total` with minor rounding discrepancy tolerance (<= ₹1.00). Discrepancies > ₹1.00 trigger `ValidationStatus.INVALID_MATH` and mark document for human review.
- **Enricher**: Maps merchant candidates through the Prompt 12 Merchant Repository and normalizer to assign canonical merchant IDs and suggested expense categories.

### 2.4 Transaction Matching
- Cross-references extracted total and transaction dates within a configurable date window (`+/- 5 days`) against workspace transactions.
- Produces ranked candidate matches classified as `EXACT`, `CANDIDATE`, `AMBIGUOUS`, or `NONE`.

### 2.5 Explicit Confirmation Gate
Only when an authorized user clicks **Confirm & Post Transaction** with a selected debit financial account does the system invoke `TransactionService.intake_transaction` to generate an immutable, double-entry financial record and link it to the document via `DocumentTransactionAssociation`.

---

## 3. Database Schema Reference

| Table | Purpose |
|---|---|
| `financial_documents` | Metadata, file path, size, MIME type, checksum, status |
| `document_extractions` | Raw OCR text, structured entities, field confidences, overall confidence, validation warnings |
| `document_reviews` | Audit log of human field corrections, reviewer ID, diffs, and review action |
| `document_transaction_associations` | Bidirectional link between verified document and authoritative transaction |

---

## 4. Security & Privacy Guardrails
1. **Zero Credential Storage**: OCR pipelines never store CVV, ATM PINs, UPI PINs, or raw card magnetic stripe data.
2. **Anti-IDOR Defense**: All queries and file downloads enforce `workspace_id` tenant scoping. A user from Workspace A cannot query, download, or verify documents from Workspace B.
3. **Audit Trail**: Every modification and confirmation action records reviewer identity, timestamps, and before/after payloads.
