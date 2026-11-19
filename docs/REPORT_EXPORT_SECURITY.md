# ARTHSAVORA — REPORT EXPORT SECURITY & DEFENSE

## 1. Threat Model & CSV Formula Injection (CWE-1236)

When exporting financial workpapers to CSV or Excel spreadsheet formats, malicious or untrusted input strings (such as customer names, invoice descriptions, transaction memos, or notes) can trigger dynamic formula execution in software like Microsoft Excel, LibreOffice Calc, or Google Sheets.

### 1.1 Dangerous Trigger Characters
Any cell starting with:
- `=` (Formula execution)
- `+` (Arithmetic prefix evaluation)
- `-` (Arithmetic prefix evaluation)
- `@` (Command prefix / DDE execution)
- Tab (`\t`) or Carriage Return (`\r`)

### 1.2 Mitigation & Deterministic Sanitization
ARTHSAVORA enforces strict output sanitization on every emitted CSV and tabular cell via `sanitize_csv_cell`:

```python
def sanitize_csv_cell(value: Any) -> str:
    """
    Sanitizes cell contents against CSV Formula Injection (CWE-1236).
    Prefixes leading '=', '+', '-', or '@' with a single quote (').
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@"):
        return "'" + val_str
    return val_str
```

---

## 2. Cryptographic Snapshot Integrity & SHA-256 Checksums

1. Every generated report snapshot is computed into a deterministic JSON representation.
2. The system computes a SHA-256 cryptographic digest of the snapshot:
   $$\text{Checksum} = \text{SHA256}(\text{JSON Payload})$$
3. The checksum is persisted in `generated_reports.checksum` and returned in the HTTP headers (`ETag: "sha256-..."`) during export downloads.
4. If an exported document's checksum does not match the database record, tampering or corruption is instantly proven.

---

## 3. RBAC & Export Permissions

Exports require explicit `EXPORT_FINANCIAL_REPORTS` (`reports:export`) permission, restricting file downloads to workspace owners, administrators, or designated external accountants.
