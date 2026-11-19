# ARTHSAVORA Financial Provider Security, Privacy & RBAC

## 1. Zero Credential Storage Policy

ARTHSAVORA operates on a strict **Zero Banking Credential Storage** security posture:
- **No Netbanking Credentials**: The system never accepts, transmits, processes, or stores user internet banking usernames, passwords, transaction passwords, or MPINs.
- **No Card Security Data**: Card verification values (CVVs), ATM PINs, and full primary account numbers (PAN) are never requested or stored.
- **No Scraping Bots**: ARTHSAVORA forbids headless browser screen-scraping of online banking portals.
- **Regulated Tokenization**: All external connectivity relies exclusively on cryptographically signed OAuth2 tokens or RBI-authorized Account Aggregator consent artefacts.

---

## 2. Multi-Tenant Isolation & Anti-IDOR Protections

Every table and query in the financial connection subsystem is strictly bounded by `workspace_id`:
1. **Tenant Filtering**: Queries for connections, accounts, sync jobs, and reconciliations explicitly filter by `workspace_id` to prevent Insecure Direct Object Reference (IDOR) attacks across workspaces.
2. **Permission Checks**: All REST API endpoints enforce workspace membership and explicit RBAC permissions via `require_permission(...)`.

---

## 3. RBAC Permissions Matrix

The following granular permissions govern financial connections:
- **`connections:view` (`Permission.VIEW_FINANCIAL_CONNECTIONS`)**: Read-only access to view connected institutions, discovered accounts, sync status, and reconciliation logs.
- **`connections:manage` (`Permission.MANAGE_FINANCIAL_CONNECTIONS`)**: Administrative access to initiate new connections, link/unlink accounts, revoke consents, and disconnect integrations.
- **`connections:sync` (`Permission.SYNC_FINANCIAL_CONNECTIONS`)**: Operational access to trigger manual data synchronizations and resolve reconciliation variances.

### Role Mappings Across Workspace Types:
| Workspace Type | Role | `connections:view` | `connections:manage` | `connections:sync` |
| :--- | :--- | :---: | :---: | :---: |
| **Personal** | `owner` | ✅ | ✅ | ✅ |
| **Family** | `family_head` / `owner` | ✅ | ✅ | ✅ |
| **Family** | `adult_member` / `member` | ✅ | ❌ | ✅ |
| **Family** | `viewer` | ✅ | ❌ | ❌ |
| **Business** | `owner` / `admin` | ✅ | ✅ | ✅ |
| **Business** | `accountant` | ✅ | ❌ | ✅ |
| **Business** | `member` / `employee` | ❌ | ❌ | ❌ |
| **Business** | `viewer` | ✅ | ❌ | ❌ |

---

## 4. Tamper-Evident Audit Logging (`connection_audit_events`)

All lifecycle mutations generate an immutable audit log entry in `connection_audit_events`:
- `event_type`: e.g. `connection_initiated`, `connection_authorized`, `account_linked`, `account_unlinked`, `consent_revoked`, `sync_completed`, `variance_resolved`.
- `severity`: `info`, `warning`, `critical`.
- `user_id`: UUID of the authenticated actor.
- `workspace_id`: Tenancy boundary.
- `metadata`: JSON payload recording context details (e.g. masked identifiers, provider code, reason strings).
- `ip_address` & `user_agent`: Recorded via request middleware.
