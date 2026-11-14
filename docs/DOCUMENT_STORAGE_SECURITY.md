# Document Storage, File Integrity and Security Architecture

## 1. Executive Summary

Financial documents (such as invoices, point-of-sale slips, and tax statements) contain highly sensitive commercial and personal information. Improper handling introduces vulnerabilities including unauthorized document access (Insecure Direct Object References - IDOR), remote code execution via malicious file uploads, directory traversal, and violation of financial privacy regulations.

This specification details the defensive security controls, file integrity checks, tenant partitioning, and zero-credential storage policies implemented across [document_service.py](file:///d:/Arthsavora/backend/app/services/document/document_service.py) and [document_routes.py](file:///d:/Arthsavora/backend/app/api/v1/document_routes.py).

---

## 2. Secure File Ingress & Validation Pipeline

Before any uploaded file is persisted to disk, it passes through an uncompromising validation gate:

```
[Incoming File Stream]
         │
         ▼
[Size Validation (<= 15 MB)] ──(Exceeds)──> [HTTP 400 Bad Request]
         │ (Pass)
         ▼
[Magic-Byte Header Inspection] ──(Invalid)──> [HTTP 400 Unsupported Format]
         │ (Pass)
         ▼
[SHA-256 Checksum Calculation]
         │
         ▼
[Workspace Deduplication Check] ──(Duplicate)──> [Return Existing Document ID]
         │ (Unique)
         ▼
[Sanitized Storage Path Generation]
         │
         ▼
[Atomic Disk Write (storage/documents/...)]
```

### 2.1 Magic-Byte Verification (True MIME Detection)
Attackers frequently disguise executable scripts or malicious binaries by renaming file extensions (e.g., `payload.php.png`). The upload service strictly checks the file's binary magic bytes in memory:

| Format | Magic Byte Header | Accepted MIME Type |
|---|---|---|
| **JPEG** | `\xFF\xD8\xFF` | `image/jpeg` |
| **PNG** | `\x89PNG\r\n\x1a\n` | `image/png` |
| **WebP** | `RIFF....WEBP` | `image/webp` |
| **PDF** | `%PDF-` (`\x25\x50\x44\x46\x2D`) | `application/pdf` |

Any file whose leading binary signature fails to match these four signatures is rejected immediately.

### 2.2 File Size Constraints
The maximum permissible file size is strictly capped at **15 Megabytes** (`MAX_DOCUMENT_SIZE_BYTES = 15 * 1024 * 1024`). Files exceeding this limit are terminated before consuming disk or processing memory.

### 2.3 SHA-256 Integrity & Deduplication
On ingress, the service computes the cryptographic SHA-256 hash of the complete byte stream:
```python
file_hash = hashlib.sha256(content).hexdigest()
```
If an identical file hash already exists within the current workspace, the upload service returns the existing document record rather than duplicating storage and triggering redundant OCR workloads.

---

## 3. Directory Layout & Tenant Isolation

### 3.1 Partitioned Storage Structure
Uploaded files are stored in a hierarchical, multi-tenant directory structure isolated by `workspace_id`:

```
storage/
└── documents/
    └── {workspace_id}/
        └── {document_id}/
            ├── original.png          # Bit-exact preserved original upload
            ├── preprocessed.png      # Enhanced, contrast-adjusted OCR input
            └── metadata.json         # Storage metadata and checksum verification
```

### 3.2 Directory Traversal Defenses
To prevent directory traversal attacks (e.g. filenames containing `../../etc/passwd`), all path resolution:
1. Strips any relative path components (`..`, `.`, `/`, `\`).
2. Generates file paths using server-controlled UUIDs (`workspace_id`, `document_id`).
3. Uses `Path.resolve()` to ensure target directories remain strictly inside the configured storage root.

---

## 4. Anti-IDOR Authorization Controls

Insecure Direct Object Reference (IDOR) attacks occur when an authenticated user attempts to access resources belonging to a different tenant by altering the URL ID.

Arthsavora prevents IDOR vulnerabilities at two distinct layers:

### 4.1 FastAPI Workspace Dependency Injection
All document routes require the `get_workspace_context` dependency:
```python
@router.get("/{document_id}/file")
async def get_document_file(
    document_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    ...
):
```
The endpoint validates that the user is an active member of `ctx.workspace.id` and holds the required permission (`Permission.VIEW_DOCUMENTS`).

### 4.2 Multi-Tenant Database Query Scoping
The `DocumentRepository` executes all document queries through `WorkspaceScopedRepository`:
```python
async def get_by_id_scoped(self, workspace_id: UUID, document_id: UUID):
    stmt = (
        select(FinancialDocument)
        .where(
            FinancialDocument.id == document_id,
            FinancialDocument.workspace_id == workspace_id,
        )
    )
```
If a user in Workspace A attempts to request a `document_id` belonging to Workspace B, the query yields `None` and raises a `404 Not Found` exception, completely preventing cross-tenant leakage.

---

## 5. Zero-Credential Storage Policy

Under RBI (Reserve Bank of India) guidelines, PCI-DSS, and IT Act standards, sensitive payment authentication credentials must never be stored on internal application servers.

The extraction pipeline enforces the following invariants:
- **Card Security Codes (CVV / CVC)**: Regex extractors actively scrub 3-4 digit card security codes if present on paper receipts.
- **PINs / MPINs**: ATM PINs and UPI MPINs are never extracted or stored.
- **Card Numbers**: Only masked PAN representations (last 4 digits, e.g. `**** 1234`) are retained for payment method identification.
- **Bank Passwords / OTPs**: Explicitly ignored by token analyzers.

---

## 6. Secure Authenticated File Streaming

Files are never served via public static file directories (e.g. `public/` or standard web server directories). All document downloads and image previews require an authenticated HTTP request:
- **Endpoint**: `GET /api/v1/workspaces/{workspace_id}/documents/{document_id}/file`
- **Headers**:
  - `Content-Type`: Exact detected MIME type (`image/png`, `application/pdf`, etc.).
  - `Content-Disposition`: `inline; filename="receipt.png"` for browser viewing.
  - `Cache-Control`: `private, no-cache, no-store, must-revalidate` to prevent intermediary caching of sensitive financial records.

---

## 7. Related Architectural References

- [Receipt Intelligence Architecture](file:///d:/Arthsavora/docs/RECEIPT_INTELLIGENCE_ARCHITECTURE.md)
- [Image Preprocessing Pipeline](file:///d:/Arthsavora/docs/IMAGE_PREPROCESSING_PIPELINE.md)
- [Document Review Workflow](file:///d:/Arthsavora/docs/DOCUMENT_REVIEW_WORKFLOW.md)
- [Database Architecture](file:///d:/Arthsavora/docs/DATABASE_ARCHITECTURE.md)
