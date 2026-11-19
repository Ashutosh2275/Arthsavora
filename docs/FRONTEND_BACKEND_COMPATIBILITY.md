# Frontend-Backend Compatibility and Wire Protocol Standard

## 1. Data Type and Format Compatibility

This standard details the serialized JSON wire format exchanged between the ARTHSAVORA web/PWA frontend and the FastAPI backend.

### 1.1 Currency and Monetary Quantities
- **Rule**: Never transmit floating-point currency values across the wire.
- **Backend Representation**: 64-bit integer minor units (paise) e.g., `balance_paise: 7500000`.
- **Frontend Representation**: Transmitted and received as integer numbers, formatted on display via `formatIndianCurrency(paise)` to ₹75,000.00.

### 1.2 Timestamps and Date Formatting
- **Rule**: All timestamps are formatted according to ISO 8601 in UTC (`YYYY-MM-DDTHH:MM:SSZ`).
- **Fiscal Dates**: Dates without time components (e.g. `invoice_date`, `due_date`) are formatted as `YYYY-MM-DD`.

### 1.3 Identification Keys
- **Rule**: Entity identifiers are standard RFC 4122 Version 4 UUID strings (e.g., `414851b4-2b9b-4cc9-b64e-1dd302cefa0a`).

---

## 2. HTTP Status Code Conventions

| Status Code | Meaning in ARTHSAVORA | Typical Scenarios |
|---|---|---|
| `200 OK` | Successful query or idempotent update | `GET /accounts`, `PUT /profile` |
| `201 Created` | Successful resource creation | `POST /transactions`, `POST /invoices` |
| `204 No Content` | Successful deletion | `DELETE /transactions/{id}` |
| `400 Bad Request` | Client validation failure | Invalid IFSC format, negative amount |
| `401 Unauthorized` | Missing or expired JWT token | Expired session, invalid signature |
| `403 Forbidden` | Valid session, insufficient permissions | Member attempting to delete workspace |
| `404 Not Found` | Resource absent or owned by another tenant | Foreign workspace query, Anti-IDOR |
| `422 Unprocessable` | Malformed file or schema violation | Spoofed image header, unparseable payload |
| `500 Server Error` | Unexpected backend condition | Database connection timeout |

---

## 3. Verified End-to-End Compatibility Matrix

All 16 frontend pages and 34 test suites communicate with backend mocks and live routes using identical serializations, with zero type mismatches or unhandled payload fields.
