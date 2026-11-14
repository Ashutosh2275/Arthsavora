# ARTHSAVORA — ROLE & PERMISSION MATRIX (RBAC)

## 1. Executive Summary

Arthsavora enforces role-based access control (RBAC) contextualized by the active workspace type. A user's privileges are determined by the combination of:
1. The **Workspace Type** (`personal`, `family`, `business`).
2. The user's **Membership Role** within that workspace.
3. The specific granular **Permission** requested by the API route.

---

## 2. Permission Enumeration

Arthsavora defines 16 granular application-level permissions:

| Permission | Identifier | Description |
| :--- | :--- | :--- |
| `VIEW_WORKSPACE` | `workspace:view` | Inspect workspace profile, settings, and base metadata |
| `UPDATE_WORKSPACE` | `workspace:update` | Edit workspace title, currency, timezone, and country |
| `ARCHIVE_WORKSPACE` | `workspace:archive` | Transition workspace into read-only archived state |
| `RESTORE_WORKSPACE` | `workspace:restore` | Restore archived workspace back to active status |
| `DELETE_WORKSPACE` | `workspace:delete` | Soft-delete workspace and initiate data purge |
| `TRANSFER_OWNERSHIP`| `workspace:transfer_ownership` | Hand over primary legal ownership to an active member |
| `VIEW_MEMBERS` | `members:view` | View active members, roles, and invitation status |
| `INVITE_MEMBERS` | `members:invite` | Issue cryptographically hashed workspace invitations |
| `UPDATE_MEMBER_ROLE`| `members:update_role` | Promote or demote member roles within allowable matrix |
| `REMOVE_MEMBERS` | `members:remove` | Revoke a member's workspace access |
| `VIEW_ACCOUNTS` | `accounts:view` | View financial accounts, balances, and institutions |
| `MANAGE_ACCOUNTS` | `accounts:manage` | Open, modify, archive, or connect financial accounts |
| `VIEW_TRANSACTIONS` | `transactions:view` | View transaction history, ledgers, and audit entries |
| `CREATE_TRANSACTIONS`| `transactions:create`| Record expenses, income, transfers, and journal entries |
| `UPDATE_TRANSACTIONS`| `transactions:update`| Edit categorizations, notes, tags, and attachments |
| `MANAGE_BUSINESS_PROFILE` | `business:manage_profile` | Modify GSTIN, PAN, FY dates, and statutory metadata |
| `VIEW_FAMILY_FINANCE` | `family:view` | View family overview, shared budgets, and settlement recommendations |
| `MANAGE_FAMILY_FINANCE` | `family:manage` | Configure household settings, currency, and settlement cadence |
| `MANAGE_FAMILY_ALLOCATIONS` | `family:allocations:manage` | Create, revise, or cancel shared expense allocations |
| `MANAGE_FAMILY_CONTRIBUTIONS` | `family:contributions:manage` | Record, confirm, or waive pool contributions |
| `MANAGE_FAMILY_SETTINGS` | `family:settings:manage` | Modify family profile and restricted member view policies |

---

## 3. Comprehensive Role-Permission Matrix

### 3.1 Personal Workspace
In a Personal Workspace, the user is the sole owner. No sub-roles exist.

| Permission | Owner |
| :--- | :---: |
| `VIEW_WORKSPACE` | Yes |
| `UPDATE_WORKSPACE` | Yes |
| `ARCHIVE_WORKSPACE` | Yes |
| `RESTORE_WORKSPACE` | Yes |
| `DELETE_WORKSPACE` | Yes |
| `VIEW_MEMBERS` | Yes |
| `INVITE_MEMBERS` | No (Personal workspaces do not accept members) |
| `VIEW_ACCOUNTS` | Yes |
| `MANAGE_ACCOUNTS` | Yes |
| `VIEW_TRANSACTIONS` | Yes |
| `CREATE_TRANSACTIONS` | Yes |
| `UPDATE_TRANSACTIONS` | Yes |

---

### 3.2 Family Workspace
Family workspaces coordinate household finances while protecting dependent members and sensitive accounts.

| Permission | Owner | Admin | Member | Restricted | Viewer |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `VIEW_WORKSPACE` | Yes | Yes | Yes | Yes | Yes |
| `UPDATE_WORKSPACE` | Yes | Yes | No | No | No |
| `ARCHIVE_WORKSPACE` | Yes | Yes | No | No | No |
| `RESTORE_WORKSPACE` | Yes | Yes | No | No | No |
| `DELETE_WORKSPACE` | Yes | No | No | No | No |
| `TRANSFER_OWNERSHIP` | Yes | No | No | No | No |
| `VIEW_MEMBERS` | Yes | Yes | Yes | Yes | Yes |
| `INVITE_MEMBERS` | Yes | Yes | No | No | No |
| `UPDATE_MEMBER_ROLE` | Yes | Yes | No | No | No |
| `REMOVE_MEMBERS` | Yes | Yes | No | No | No |
| `VIEW_ACCOUNTS` | Yes | Yes | Yes | No | Yes |
| `MANAGE_ACCOUNTS` | Yes | Yes | No | No | No |
| `VIEW_TRANSACTIONS` | Yes | Yes | Yes | No | Yes |
| `CREATE_TRANSACTIONS` | Yes | Yes | Yes | No | No |
| `UPDATE_TRANSACTIONS` | Yes | Yes | No | No | No |
| `VIEW_FAMILY_FINANCE` | Yes | Yes | Yes | Yes | Yes |
| `MANAGE_FAMILY_FINANCE` | Yes | Yes | No | No | No |
| `MANAGE_FAMILY_ALLOCATIONS` | Yes | Yes | Yes | No | No |
| `MANAGE_FAMILY_CONTRIBUTIONS` | Yes | Yes | Self Only | No | No |
| `MANAGE_FAMILY_SETTINGS` | Yes | Yes | No | No | No |

---

### 3.3 Business Workspace
Business workspaces support statutory operations, general ledger accounting, approvals, and staff logging.

| Permission | Owner | Admin | Accountant | Approver | Staff | Viewer |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `VIEW_WORKSPACE` | Yes | Yes | Yes | Yes | Yes | Yes |
| `UPDATE_WORKSPACE` | Yes | Yes | No | No | No | No |
| `ARCHIVE_WORKSPACE` | Yes | Yes | No | No | No | No |
| `RESTORE_WORKSPACE` | Yes | Yes | No | No | No | No |
| `DELETE_WORKSPACE` | Yes | No | No | No | No | No |
| `TRANSFER_OWNERSHIP` | Yes | No | No | No | No | No |
| `VIEW_MEMBERS` | Yes | Yes | No | Yes | No | Yes |
| `INVITE_MEMBERS` | Yes | Yes | No | No | No | No |
| `UPDATE_MEMBER_ROLE` | Yes | Yes | No | No | No | No |
| `REMOVE_MEMBERS` | Yes | Yes | No | No | No | No |
| `VIEW_ACCOUNTS` | Yes | Yes | Yes | Yes | Yes | Yes |
| `MANAGE_ACCOUNTS` | Yes | Yes | Yes | No | No | No |
| `VIEW_TRANSACTIONS` | Yes | Yes | Yes | Yes | Yes | Yes |
| `CREATE_TRANSACTIONS` | Yes | Yes | Yes | Yes | Yes | No |
| `UPDATE_TRANSACTIONS` | Yes | Yes | Yes | No | No | No |
| `MANAGE_BUSINESS_PROFILE`| Yes | Yes | No | No | No | No |

---

## 4. Enforcement Mechanism in Code

### 4.1 Dependency Injection (`require_permission`)
In FastAPI routes, permissions are declaratively enforced using dependency injection:

```python
@router.patch("/{workspace_id}/members/{membership_id}")
async def update_member_role(
    membership_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.UPDATE_MEMBER_ROLE)),
    session: AsyncSession = Depends(get_db_session),
):
    ...
```

### 4.2 Hierarchy & Safety Invariants
1. **No Self-Elevation:** A member cannot grant themselves permissions or assign the `owner` role.
2. **Owner Immunity:** An owner cannot be demoted or removed via standard membership endpoints; ownership transfer must be executed explicitly.
3. **Workspace Type Validation:** Attempting to assign a role unsupported by the workspace type (e.g. `accountant` in a `family` workspace) fails with HTTP 422.
