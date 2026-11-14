# Arthsavora Anomaly Privacy, Security & Isolation Boundaries

## 1. Zero Cloud-Leakage Guarantee

All anomaly detection, feature engineering, statistical models, and machine learning inferences execute **entirely within the local deployment perimeter**:
- **No Third-Party AI/LLM Calls**: Financial transactions, descriptions, amounts, account balances, and merchant records are never transmitted to OpenAI, Anthropic, Google Gemini, or any external public LLM endpoint for anomaly scoring.
- **Local scikit-learn & NumPy Runtimes**: The Isolation Forest, MAD, and IQR algorithms run on local CPU threads using deterministic seeds (`random_state=42`).

---

## 2. Multi-Tenant Cryptographic & Logical Isolation

### PostgreSQL Row-Level & Schema Isolation
Every table in the anomaly module enforces tenancy with mandatory foreign key references and indexes:
- `anomaly_detections.workspace_id`
- `anomaly_reviews.workspace_id`
- `detection_rules.workspace_id`
- `detection_exceptions.workspace_id`

### Repository Enforcement
Every database query in `AnomalyRepository` strictly validates `workspace_id == current_workspace_id`. Cross-workspace reads, reviews, or rule mutations immediately trigger `NotFoundException` or `PermissionDeniedException`.

---

## 3. RBAC Permissions & Role Scopes

The permissions module (`backend/app/core/permissions.py`) controls anomaly features through fine-grained capabilities:

| Permission String | Description | Allowed Roles |
| :--- | :--- | :--- |
| `anomalies:view` | View anomaly feeds, trends, summaries, and rules. | Owner, Admin, Member, Viewer, Accountant |
| `anomalies:manage` | Acknowledge, review, update rules, and create whitelist exceptions. | Owner, Admin, Approver, Accountant (Business) |

### Workspace Role Mapping

- **Personal Workspaces**:
  - `owner`: full view and management rights.
- **Family Workspaces**:
  - `owner` / `admin`: full management and whitelist privileges.
  - `member` / `viewer`: view-only permissions.
- **Business Workspaces**:
  - `owner` / `admin`: complete configuration and review authority.
  - `accountant`: can review anomalies, mark expected, and verify statement balance discrepancies.
  - `staff` / `viewer`: view-only or restricted access.

---

## 4. Immutable Audit Trails

All human interventions are permanently recorded in `anomaly_reviews`:
- Reviewer user ID (`reviewer_id`).
- Exact timestamp with timezone (`created_at`).
- Action taken (`action`), formal reason code (`reason`), and commentary (`notes`).
- Audit entries are strictly append-only; updates and hard deletes are disabled.
