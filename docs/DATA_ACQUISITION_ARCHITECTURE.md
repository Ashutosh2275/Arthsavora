# ARTHSAVORA — FINANCIAL DATA ACQUISITION ARCHITECTURE

## 1. Executive Summary & Core Objective

The **Financial Data Acquisition & Statement Import Module** establishes an institutional-grade, multi-format pipeline for bringing external financial statements and transaction records into the Arthsavora ecosystem. 

Financial acquisition operates under non-negotiable architectural mandates:
1. **Explicit Review & Confirmation**: External statement data is staged in candidate tables (`import_candidates`). No statement ingestion ever silently creates operational transactions or ledger journal entries without user confirmation.
2. **Double-Entry Cohesion**: Confirmed statement items are converted into operational `Transaction` records and posted atomically to the General Ledger via `LedgerService`, guaranteeing the trial balance invariant ($\sum \text{Debits} = \sum \text{Credits}$).
3. **Exact Monetary Precision**: All balances and transaction values are stored as integer minor units (`paise` for INR) and high-precision `Numeric(18, 4)`. Floating-point arithmetic is strictly prohibited.
4. **Tenant Isolation**: Complete row-level and workspace-level isolation enforces that no cross-workspace access or data contamination is possible (anti-IDOR defense).
5. **Idempotency & Deduplication**: Multi-level deduplication prevents identical files from being uploaded twice without explicit user consent, and prevents re-importing identical or probable transactions.

---

## 2. Ingestion Domain Hierarchy & Entity Lifecycle

The data acquisition domain model is structured in a 4-tier relational hierarchy:

```
[ImportJob] (Lifecycle state machine, storage reference, MIME/magic verification)
    └── [ImportFile / Storage Asset] (SHA-256 hashed, private local directory isolation)
    └── [ImportBatch] (Header mapping, format detection, opening/closing balance metadata)
            └── [ImportCandidate] (Normalized staging records: status, confidence, duplicate flags)
                    └── [Transaction & General Ledger Journal Entries] (Upon atomic confirmation)
```

### Entity Responsibilities

1. **`ImportJob`**: Tracks the overall import process, uploaded file metadata (size, MIME type, SHA-256 hash), target account ID, workspace ID, user ID, record count statistics (`valid_records`, `invalid_records`, `duplicate_records`, `imported_records`), and status lifecycle.
2. **`ImportBatch`**: Represents a parsed logical batch of records from a file (or multi-sheet workbook), containing the detected format (`csv`, `xlsx`, `pdf_text`, `pdf_ocr`), column mapping applied, opening balance, closing balance, computed balance, and reconciliation discrepancy.
3. **`ImportCandidate`**: A staged, individual transaction candidate containing raw unparsed dictionary data, normalized fields (`transaction_date`, `amount`, `amount_paise`, `direction`, `transaction_type`), validation status (`valid`, `invalid`, `ambiguous`), validation error messages, duplicate status (`none`, `exact`, `probable`), confidence score, and confirmation state.

### Lifecycle State Machine

```
[ UPLOADED ] 
     │
     ▼
[ VALIDATING ] ──(Checksum/Security Check Failure)──► [ FAILED ]
     │
     ▼
[ PROCESSING ] ──(Parsing / Normalization / Deduplication)
     │
     ▼
[ AWAITING_REVIEW ] ◄──(User edits candidates / toggles selection)
     │
     ├──────────────────────┐
     ▼                      ▼
[ CONFIRMED ]          [ CANCELLED ]
     │
     ▼
[ COMPLETED ] / [ PARTIALLY_CONFIRMED ]
```

---

## 3. Supported Input Formats

| Format | Parsing Engine | Capabilities & Safeguards |
| :--- | :--- | :--- |
| **CSV** | `CsvStatementParser` (Python `csv` + `chardet`) | Auto dialect sniffing (comma, semicolon, tab, pipe), UTF-8 / Latin-1 / CP1252 encoding detection, Indian bank headers (HDFC, SBI, ICICI, Axis, Kotak), summary/total row suppression. |
| **Excel (XLSX)** | `XlsxStatementParser` (`openpyxl`) | **Formula execution disabled** (`data_only=True`, `read_only=True`), memory-bounded streaming, multi-sheet inspection and targeted sheet selection. |
| **Digital PDF** | `PdfStatementParser` (`pdfplumber`) | Digital vector text extraction, table boundary parsing, text coordinate fallback for borderless tables, opening/closing balance regex extraction. |
| **Scanned PDF / Image** | `OcrStatementAdapter` (`pytesseract` / Tesseract OCR) | Optical Character Recognition for scanned statements, image pre-processing (grayscale, thresholding), low-confidence flagging (`0.70` baseline). |

---

## 4. Multi-Level Deduplication Architecture

To maintain financial ledger purity, Arthsavora implements three defensive deduplication gates:

1. **Gate 1: File-Level Deduplication (SHA-256 Checksum)**
   - Prior to processing, the file's SHA-256 hash is compared against all existing jobs in the workspace.
   - Uploading the identical file raises `DuplicateImportError` unless `allow_duplicate_file=True` is explicitly specified.

2. **Gate 2: Exact Reference Deduplication**
   - Candidate reference numbers (`Chq/Ref No`, `UTR`, `UPI Ref`, `NEFT Ref`) are matched against existing posted/pending transactions in the workspace.
   - Exact matches are marked `duplicate_status = "exact"`, de-selected from import by default (`selected_for_import = False`), and linked to the existing transaction ID.

3. **Gate 3: Probable & Fuzzy Deduplication**
   - For candidates lacking explicit reference IDs, a window query ($\pm 1$ day, same account, same amount in paise, same direction) identifies potential duplicates.
   - Marked `duplicate_status = "probable"` with an explanatory reason (`Probable duplicate: matches transaction on YYYY-MM-DD`).

4. **Gate 4: Intra-Batch Deduplication**
   - Protects against duplicate rows contained within the single statement file itself. Subsequent identical rows in the same batch are marked `duplicate_status = "exact"` with reason `Identical transaction found earlier in this statement file`.

---

## 5. Security & Isolation Invariants

- **Storage Sandboxing**: Statement files are stored in `storage/imports/{workspace_id}/{job_id}/{random_uuid}.ext`. Filenames are stripped of path traversal characters (`..`, `/`, `\`).
- **File Size Bounding**: Enforced 10 MB strict limit (`MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`).
- **MIME & Magic Byte Verification**: File headers are validated against cryptographic magic signatures (`%PDF-`, `PK\x03\x04`). Executables or masquerading files are immediately rejected.
- **Tenant Authorization**: All endpoints enforce `Permission.IMPORT_DATA` or `Permission.VIEW_IMPORTS` scoped to the active workspace context.
