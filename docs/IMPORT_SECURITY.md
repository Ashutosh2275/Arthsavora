# ARTHSAVORA — DATA IMPORT SECURITY & TENANCY ISOLATION

## 1. Threat Model & Defensive Posture

Financial statement processing is a high-risk security boundary:
- Statement files originate from untrusted external sources (user desktop uploads, web banking exports, scanned attachments).
- Statements may contain malformed data, malicious formula injections (CSV/Excel macro injection), path traversal attacks, or embedded executable binaries.
- Staged records contain sensitive personal/corporate banking data (account masks, transaction narrations, balance levels).

---

## 2. Defensive Controls & Mitigation Layers

### 2.1 File Size Bounding & DoS Mitigation
- Strict maximum limit of 10 MB per file (`MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`).
- Uploads exceeding this limit are aborted immediately during stream intake, raising `FileTooLargeError`.

### 2.2 Magic Byte & Header Verification
File extensions can be easily spoofed (e.g. an `.exe` renamed to `.pdf` or `.csv`). The system inspects file headers against cryptographic magic byte signatures:

| Format | Allowed Extensions | Required Magic Byte Signatures |
| :--- | :--- | :--- |
| **PDF** | `.pdf` | Must begin with `%PDF-` (`b"%PDF-"`) |
| **XLSX** | `.xlsx` | Must begin with PK Zip container header (`b"PK\x03\x04"`) |
| **CSV** | `.csv`, `.txt` | Plain text verified via UTF-8/Latin-1/CP1252 character validation |

Files failing magic byte inspection raise `UnsafeFileError`.

### 2.3 Formula Execution Defense (Excel & CSV Injection)
- **Excel (`openpyxl`)**: All workbooks are opened with:
  ```python
  openpyxl.load_workbook(..., data_only=True, read_only=True)
  ```
  This guarantees that Excel formulas (e.g. `=HYPERLINK()`, `=CMD()`, `=DDE()`) are never evaluated by the server; only pre-calculated cached values are extracted.
- **CSV Sanitization**: When rendering descriptions or exporting to CSV, leading formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) are sanitized to prevent client-side spreadsheet injection when users download financial reports.

### 2.4 Sandboxed File System Storage
- Uploaded files are never stored under their original filenames or in public web directories.
- Stored exclusively in a protected local path:
  ```
  storage/imports/{workspace_id}/{job_id}/{random_uuid}.{ext}
  ```
- Original filenames are sanitized to prevent directory traversal (`../`, `..\\`).
- Access to uploaded source files requires workspace authorization; direct public URL serving is prohibited.

### 2.5 Multi-Workspace Tenancy & Anti-IDOR Protections
- All database queries filter on `workspace_id`.
- Attempting to inspect an `ImportJob`, `ImportBatch`, or `ImportCandidate` belonging to another workspace returns a `404 Not Found` (never `403 Forbidden` to prevent object existence enumeration).
- Confirmed transactions inherit the caller's authorized `workspace_id`.

### 2.6 Role-Based Access Control (RBAC)
Import operations are governed by dedicated fine-grained permissions:
- `Permission.IMPORT_DATA`: Granted to `owner`, `admin`, and `treasurer` (business), and `head_of_household`, `adult_member` (family). Prohibited for `auditor`, `member`, `child`.
- `Permission.VIEW_IMPORTS`: Granted to all workspace roles except `child`.
