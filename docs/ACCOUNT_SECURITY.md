# Arthsavora — Financial Account Security & Multi-Tenant Isolation

## 1. Security Architecture Principles

Financial accounts represent sensitive monetary assets and liabilities. The Arthsavora platform implements defense-in-depth protections across four key pillars:
1. **Multi-Tenant Isolation & Anti-IDOR (Insecure Direct Object Reference).**
2. **Masked Financial Identifiers & PCI-DSS / RBI Compliance.**
3. **Duplicate External Account Prevention.**
4. **Role-Based Permission Enforcement.**

---

## 2. Multi-Tenant Isolation & Anti-IDOR Protections

Every financial account is hard-bound to a `workspace_id`. Cross-workspace boundary access is prevented at multiple layers:

### 2.1 Workspace Scoping in Repositories
Repositories never look up accounts by raw primary key alone. Every database query enforces:
```python
stmt = select(Account).where(
    Account.id == entity_id,
    Account.workspace_id == workspace_id,
    Account.is_deleted == False,
)
```

### 2.2 Uniform 404 Response (Anti-Enumeration)
If a member in Workspace A attempts to fetch, update, archive, or close an account belonging to Workspace B (even if the user has an active membership in both workspaces):
- The repository returns `None`.
- The service raises `NotFoundException(message="Financial account not found.")`.
- The API responds with HTTP `404 Not Found`.
- **Zero Information Leak:** Attackers cannot determine whether a UUID exists in another workspace.

---

## 3. Financial Identifiers & Sensitive Data Protection

Arthsavora strictly complies with Reserve Bank of India (RBI) tokenization guidelines and PCI-DSS data protection rules:
- **No Raw PAN Storage:** Primary Account Numbers (16-digit card numbers) and full bank account numbers are **never stored** in the database.
- **Masked Identifiers Only:** The `masked_identifier` column stores only truncated or masked tokens (e.g. `••••4321` or `XX8901`).
- **No Raw Banking Credentials:** Net banking passwords, PINs, OTPs, and card CVVs are never accepted or retained. External banking feeds integrate exclusively via authorized Account Aggregators (RBI-regulated NBFC-AAs) or tokenized OAuth connections.

---

## 4. Duplicate External Provider Prevention

To prevent duplicate transaction intake and accidental multiple mappings of the same bank account within a workspace, a composite unique constraint is enforced at the database level:

```sql
CONSTRAINT uq_workspace_provider_account UNIQUE (workspace_id, provider_name, provider_account_id)
```

If an external sync or manual setup attempts to link the same `provider_account_id` under the same `provider_name` in the same workspace:
- The check triggers before or during database write.
- The service raises `ConflictException(message="...", code="DUPLICATE_EXTERNAL_ACCOUNT")`.
- The API responds with HTTP `409 Conflict`.
- Note: Different workspaces may link the same external account (e.g., if a user explicitly manages the same account in personal and business contexts), but duplicate links within the same workspace are strictly prevented.

---

## 5. Role-Based Access Control (RBAC)

Financial account operations require explicit granular permissions:

| Operation | Required Permission | Allowed Roles |
| :--- | :--- | :--- |
| `GET /accounts/` (List) | `Permission.VIEW_ACCOUNTS` | `owner`, `admin`, `member`, `accountant`, `approver`, `viewer` |
| `GET /accounts/{id}` (Detail) | `Permission.VIEW_ACCOUNTS` | `owner`, `admin`, `member`, `accountant`, `approver`, `viewer` |
| `GET /accounts/{id}/balances` | `Permission.VIEW_ACCOUNTS` | `owner`, `admin`, `member`, `accountant`, `approver`, `viewer` |
| `GET /accounts/{id}/balance-history` | `Permission.VIEW_ACCOUNTS` | `owner`, `admin`, `member`, `accountant`, `approver`, `viewer` |
| `POST /accounts/` (Create) | `Permission.MANAGE_ACCOUNTS` | `owner`, `admin`, `accountant` |
| `PATCH /accounts/{id}` (Update) | `Permission.MANAGE_ACCOUNTS` | `owner`, `admin`, `accountant` |
| `POST /accounts/{id}/archive` | `Permission.MANAGE_ACCOUNTS` | `owner`, `admin` |
| `POST /accounts/{id}/restore` | `Permission.MANAGE_ACCOUNTS` | `owner`, `admin` |
| `POST /accounts/{id}/close` | `Permission.MANAGE_ACCOUNTS` | `owner`, `admin` |
| `POST /accounts/{id}/balances/snapshot` | `Permission.MANAGE_ACCOUNTS` | `owner`, `admin`, `accountant` |
