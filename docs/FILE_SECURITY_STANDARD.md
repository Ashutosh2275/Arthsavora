# ARTHSAVORA — File & Document Storage Security Standard

## 1. Overview & Risk Landscape

ARTHSAVORA accepts uploaded financial documents—including JPEG/PNG receipt photos, camera scans, and multi-page PDF vendor invoices—for automated OCR entity extraction.

Document storage introduces significant security risks:
- Malicious executables disguised as image files.
- Stored Cross-Site Scripting (XSS) embedded within SVG or PDF files.
- Zip bombs or decompressed memory exhaustion attacks.
- Path traversal vulnerabilities using directory traversal syntax (`../../`).
- Insecure direct object reference (IDOR) to access private financial documents.

This standard outlines the multi-layered security controls governing document ingestion, storage, processing, and downloads.

---

## 2. Ingestion Controls & Verification

### 2.1. Binary Magic Byte Verification
MIME types declared in HTTP headers (`Content-Type`) are untrusted client assertions. ARTHSAVORA inspects the actual binary prefix (magic bytes) of the uploaded payload:

```python
ALLOWED_MIME_TYPES = {
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # With "WEBP" at offset 8
    "application/pdf": [b"%PDF-"],
}
```

If the payload does not match the expected binary signature, the upload is rejected immediately with a 422 `ValidationException`:
```
"Unsupported or invalid document format. Only verified PDF, JPEG, PNG, and WebP files are permitted."
```

### 2.2. Strict File Size Ceiling
- **Limit:** 15 Megabytes (`MAX_DOCUMENT_SIZE_BYTES = 15 * 1024 * 1024`).
- **Enforcement:** Enforced before reading the payload into persistent storage or passing to OCR engines, protecting against storage and memory exhaustion attacks.

### 2.3. Path Traversal Elimination
- Uploaded files are **never** stored using their original client-supplied filename.
- The storage system generates a cryptographically random UUIDv4 for each document (`doc_id = uuid.uuid4()`).
- Physical storage path: `storage/documents/{workspace_id}/{doc_id}.{verified_extension}`.
- Directory traversal characters (`..`, `/`, `\`) in the original filename are stripped, and the original filename is stored strictly as sanitized metadata in the database.

---

## 3. Storage Security & Access Control

### 3.1. Tenant Isolation
- Document database records (`financial_documents`) include a mandatory `workspace_id` foreign key.
- The `DocumentRepository` executes scoped lookups (`get_by_id_scoped(document_id, workspace_id)`). If a user requests a document from another workspace, the query returns `None`, resulting in a `404 Not Found`.

### 3.2. Private Storage Buckets
- Documents are never exposed through public unauthenticated web URLs.
- In cloud deployments (Supabase Storage / AWS S3), buckets are configured as **Private / Restricted**.
- Document access requires either:
  1. Authenticated backend streaming through an authorized API endpoint (`/api/v1/documents/{id}/file`).
  2. Time-limited pre-signed URLs (15-minute maximum validity) generated on demand for authorized users.

---

## 4. Secure Deletion & Retention

When a document is deleted via `DELETE /api/v1/documents/{document_id}`:
1. Authorization check confirms the user possesses `documents:manage` permission in the active workspace.
2. The physical file is securely unlinked from the filesystem/object store.
3. The database record, extracted line items, review records, and transaction associations are removed in a single database transaction.
4. If the parent workspace directory is empty, the directory is pruned.

---

## 5. Automated Verification Results

- **MIME Magic Byte Verification:** Verified in `test_document_mime_spoofing_defense`. Shell scripts (`#!/bin/bash`) and HTML scripts (`<script>`) disguised as `.jpg` or `.pdf` are rejected.
- **Oversized Document Rejection:** Verified in `test_oversized_document_rejected`. Payloads exceeding 15 MB are rejected.
- **Cross-Tenant Document Isolation:** Verified in document repository and API test suites.
