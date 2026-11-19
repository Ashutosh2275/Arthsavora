# ARTHSAVORA — Authorization, RBAC & Multi-Tenancy Review

## 1. Overview & Tenancy Boundary

ARTHSAVORA enforces strict multi-tenancy across three distinct workspace topologies:
1. **Personal Workspace:** Single-owner boundary for private finances, personal bank accounts, investments, and personal budgeting.
2. **Family Workspace:** Collaborative household boundary balancing pooled expenses/budgets with member-level privacy protections.
3. **Small Business Workspace:** Commercial operational boundary supporting client invoicing, vendor payables, double-entry general ledger, and staff/accountant role segregation.

All resources (accounts, transactions, ledger entries, invoices, documents, budgets, reports, and AI assistant conversations) are strictly partitioned by `workspace_id`.

---

## 2. Server-Side Tenancy & IDOR Prevention

### 2.1. Resolution Mechanism
Tenant context is resolved server-side via `resolve_workspace_id` from the `X-Workspace-ID` header or path parameter.

```python
async def get_workspace_context_resolver(workspace_id: uuid.UUID, current_user: User, session: AsyncSession):
    # 1. Query workspace - 404 on missing or deleted
    if not workspace or workspace.status == WorkspaceStatus.DELETED:
        raise NotFoundException(message="Workspace not found.")
    
    # 2. Query membership - 404 on non-membership (prevent tenant enumeration)
    if not membership:
        raise NotFoundException(message="Workspace not found.")
    
    # 3. Block suspended membership
    if membership.status != "active":
        raise ForbiddenException(message="Membership inactive.", code="MEMBERSHIP_INACTIVE")
    
    # 4. Activate transaction-local PostgreSQL RLS context
    await set_tenant_context(session, workspace_id)
    return WorkspaceContext(workspace, membership, current_user, membership.role)
```

### 2.2. Critical Anti-Enumeration Principle
If User A submits a request targeting Workspace B (which User A does not belong to), the API returns **`404 Not Found`**, NOT `403 Forbidden`. This completely eliminates tenant ID enumeration and prevents attackers from discovering valid workspace UUIDs.

---

## 3. Role-Based Access Control (RBAC) Matrix

The platform defines over 45 granular permissions. Access is evaluated strictly against the user's active role within the target workspace.

### 3.1. Personal Workspace
| Role | Capabilities | Restrictions |
| :--- | :--- | :--- |
| **Owner** | Full administrative and financial control over all personal accounts, ledger postings, and AI tools. | Personal workspaces strictly enforce single-ownership. External members cannot be invited. |

### 3.2. Family Workspace
| Role | Capabilities | Restrictions |
| :--- | :--- | :--- |
| **Owner** | Full household management, member invitations, role assignment, shared accounts, family budgets, allocations. | Cannot inspect private accounts of other family members without explicit delegation. |
| **Admin** | Household administration, inviting members, managing shared accounts, budgets, and recurring commitments. | Cannot delete workspace or transfer workspace ownership. |
| **Member** | View shared accounts, log family transactions, view household budget status, use AI financial assistant. | Cannot modify workspace settings, delete shared accounts, or remove other members. |
| **Viewer** | Read-only visibility into shared accounts, family budget progress, and general notifications. | Cannot create or edit transactions, modify budgets, or export financial reports. |
| **Restricted** | Minimal view into specific allocated household expenses and assigned goals. | Strictly blocked from ledger accounts, statement imports, and financial connection management. |

### 3.3. Small Business Workspace
| Role | Capabilities | Restrictions |
| :--- | :--- | :--- |
| **Owner** | Full commercial authority: general ledger, invoice management, banking connections, GST reports, team roles. | Ultimate financial responsibility; ownership transfer requires two-step confirmation. |
| **Admin** | Manages business profile, client invoices, vendor payables, team memberships, and banking synchronizations. | Cannot delete workspace or transfer ownership. |
| **Accountant** | Full access to general ledger, journal postings, reversals, accounting periods, invoices, and GST/tax reports. | Cannot manage workspace members, modify business legal profile, or delete workspace. |
| **Staff** | Issues invoices, records payments, uploads receipt documents, logs business expenses. | Cannot access general ledger, post journal entries, view tax reports, or manage bank connections. |
| **Viewer** | Read-only visibility into business analytics, invoice summaries, and notifications. | Cannot create invoices, modify records, or post transactions. |

---

## 4. Privilege Escalation Defenses

1. **Role Modification Restrictions:** A member cannot assign a role higher than their own. Only `OWNER` or `ADMIN` can update member roles.
2. **Owner Immunity:** An `ADMIN` cannot demote or remove the `OWNER`.
3. **Self-Promotion Denial:** A user cannot update their own membership role.
4. **Immutability of Transferred Ownership:** Ownership transfer is an atomic operation requiring explicit re-assignment of roles in a single database transaction.

---

## 5. Automated Verification Results

- **IDOR Protection:** Verified in `test_cross_workspace_idor_protection`. Cross-workspace requests return `404 Not Found`.
- **Role Permissions:** Verified in `test_rbac_matrix_enforcement`. Viewer/member role boundaries enforced across Personal, Family, and Business contexts.
- **Suspended Membership:** Verified in `test_suspended_membership_rejected_403`. Inactive or suspended members are blocked immediately from all workspace endpoints.
