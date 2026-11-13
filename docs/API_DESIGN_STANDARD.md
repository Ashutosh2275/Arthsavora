# Arthsavora — API Design Standards and Conventions

## 1. Route Hierarchy and Versioning

Arthsavora enforces a predictable, versioned RESTful URL structure. The authoritative production API is rooted at `/api/v1/`:

```text
/api/v1/
├── health/
│   ├── live                      # GET: Process liveness probe
│   └── ready                     # GET: Database readiness probe
├── auth/
│   ├── register                  # POST: Provision user + personal workspace
│   ├── login                     # POST: Email/password authentication
│   ├── me                        # GET: Current authenticated user & profile
│   ├── refresh                   # POST: Renew access token via refresh token
│   └── logout                    # POST: Session revocation
└── workspaces/
    ├──                           # GET: List user's active workspaces
    ├──                           # POST: Create workspace (Personal, Family, Business)
    ├── {workspace_id}            # GET: Retrieve workspace metadata
    └── {workspace_id}/members    # GET: List members | POST: Invite/add member
```

---

## 2. HTTP Methods and Status Code Semantics

Every endpoint adheres strictly to standard HTTP semantics:

| Method | Idempotent | Safe | Typical Status Codes | Description |
| :--- | :---: | :---: | :--- | :--- |
| **`GET`** | Yes | Yes | `200 OK`, `404 Not Found` | Retrieval of entities or collections. Never alters state. |
| **`POST`** | No | No | `201 Created`, `200 OK`, `409 Conflict`, `422 Unprocessable` | Resource creation or state-transition actions (login, refresh). |
| **`PUT`** | Yes | No | `200 OK`, `404 Not Found` | Complete entity replacement. |
| **`PATCH`** | No | No | `200 OK`, `422 Unprocessable` | Partial entity update. |
| **`DELETE`**| Yes | No | `200 OK`, `204 No Content` | Soft deletion or resource removal. |

### Standard HTTP Status Codes

| Code | Classification | Trigger / Usage in Arthsavora |
| :--- | :--- | :--- |
| **`200 OK`** | Success | Successful retrieval, session refresh, or update operation. |
| **`201 Created`** | Success | Successful registration, workspace creation, or entity provisioning. |
| **`400 Bad Request`** | Client Error | Malformed request body or unrecognized parameters. |
| **`401 Unauthorized`** | Security | Missing, expired (`TOKEN_EXPIRED`), or invalid (`INVALID_TOKEN`) Bearer JWT. |
| **`403 Forbidden`** | Security | Authenticated user lacks required workspace role (`INSUFFICIENT_PERMISSIONS`) or membership is inactive. |
| **`404 Not Found`** | Client Error | Resource does not exist, or target workspace does not belong to the user (anti-IDOR). |
| **`409 Conflict`** | Client Error | Duplicate email (`EMAIL_ALREADY_REGISTERED`) or concurrent duplicate request (`CONCURRENT_REQUEST`). |
| **`422 Unprocessable Entity`** | Validation | Pydantic request payload validation failure (`REQUEST_VALIDATION_ERROR`). |
| **`429 Too Many Requests`** | Abuse Protection | Rate limit exceeded on authentication or general endpoints (`RATE_LIMIT_EXCEEDED`). |
| **`500 Internal Server Error`** | Server Error | Uncaught server exception; sanitized to prevent internal traceback leaks. |
| **`503 Service Unavailable`** | Operational | Readiness check failed; PostgreSQL database is unreachable (`DATABASE_UNAVAILABLE`). |

---

## 3. Response Conventions

### 3.1 Standard Success Envelope (`ApiResponse[T]`)
For individual resource mutations or single-entity returns:
```json
{
  "status": "success",
  "data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "Patil Family Household",
    "type": "family"
  },
  "message": "Workspace provisioned successfully."
}
```

### 3.2 Standard Paginated Envelope (`PaginatedResponse[T]`)
For all collection endpoints to guard against unbounded memory consumption:
```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

### 3.3 Pagination Query Contract
- `page`: Integer $\ge 1$ (1-indexed). Default: `1`.
- `page_size`: Integer between `1` and `100`. Default: `20`.
- SQL Offset Calculation: `offset = (page - 1) * page_size`.
- Unbounded queries (`SELECT * FROM transactions`) are strictly prohibited.

---

## 4. Standardized Error Response Contract

All error responses across FastAPI HTTP exceptions, domain exceptions, validation errors, and uncaught 500 errors adhere to a uniform JSON schema:

```json
{
  "error": {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "Invalid request parameters or payload.",
    "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "details": [
      {
        "loc": ["body", "password"],
        "msg": "String should have at least 8 characters",
        "type": "string_too_short"
      }
    ]
  }
}
```

### Error Envelope Fields
1. `code`: Stable, uppercase machine-readable string (e.g. `INVALID_CREDENTIALS`, `TOKEN_EXPIRED`, `NOT_FOUND`).
2. `message`: Human-readable summary suitable for user-facing toast alerts or logging.
3. `request_id`: Server-generated UUID matching the `X-Request-ID` response header for end-to-end tracing.
4. `details`: Array of specific field-level validation errors or context dictionaries (empty for generic errors).

---

## 5. Standard Request Headers

| Header | Required | Example | Description |
| :--- | :---: | :--- | :--- |
| **`Authorization`** | Conditional | `Bearer eyJhbGciOi...` | Standard Bearer JWT for all protected endpoints. |
| **`X-Request-ID`** | Optional | `3fa85f64-5717-4562-b3fc-2c963f66afa6` | Correlation tracking ID. If omitted, server generates one. |
| **`X-Workspace-ID`** | Conditional | `c830eb02-38e9-44be-8b2b-5e60805c8c50` | Target workspace UUID for endpoints not scoping workspace in the URL path. |
| **`Idempotency-Key`** | Optional | `tx_provision_994a32` | Unique key guarding sensitive POST mutations from replay. |
