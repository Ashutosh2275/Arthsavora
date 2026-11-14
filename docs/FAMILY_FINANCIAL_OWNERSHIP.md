# ARTHSAVORA — FAMILY FINANCIAL OWNERSHIP & ASSET GOVERNANCE

## 1. Core Ownership Philosophy

In ARTHSAVORA, legal and technical ownership of financial accounts is strictly decoupled from household visibility and domestic collaboration. 

> **Guiding Principle:** An account does not become jointly owned in law simply because it is viewed, referenced, or allocated within an ARTHSAVORA family workspace.

Financial accounts fall into two distinct structural classifications:
1. **Personal Accounts:** Opened and held by an individual user within their personal workspace. These records are cryptographically and logically isolated from all other users.
2. **Household/Family Accounts:** Accounts explicitly created inside a Family Workspace for collective household management (e.g., a shared household petty cash reserve, a joint utility fund, or an emergency reserve account created specifically for family operations).

---

## 2. Shared vs. Personal Accounts Taxonomy

```
+-----------------------------------------------------------------------------------------+
|                                    ACCOUNT TAXONOMY                                     |
|                                                                                         |
|  [ PERSONAL WORKSPACE ]                                  [ FAMILY WORKSPACE ]           |
|                                                                                         |
|  1. True Personal Account                                2. Native Family Account       |
|     * Created in personal WS                                * Created in family WS      |
|     * Zero external visibility                              * Visible to family members |
|     * Private transactions, cards, loans                    * Household utility/reserve |
|     * Fully isolated                                        * Co-managed under RBAC     |
|                                                                                         |
|                        3. Bridged Personal Account                                      |
|                           * Created in personal WS                                      |
|                           * Explicitly shared via FamilyAccountShare bridge             |
|                           * Configurable scope: BALANCE_ONLY, READ_ONLY, FULL           |
|                           * Revocable at any moment by owner                            |
+-----------------------------------------------------------------------------------------+
```

### 2.1 Native Family Accounts
- **Creation:** Initiated by a Workspace Owner or Admin within the Family Workspace.
- **Ownership:** Attributed to the Family Workspace entity (`account.workspace_id == family_ws.id`).
- **Access:** Governed by the workspace's Role-Based Access Control (RBAC). Members with `VIEW_ACCOUNTS` can inspect the balance; members with `MANAGE_ACCOUNTS` can reconcile or configure settings.
- **De-linking:** If the family workspace is archived, native family accounts remain archived within that workspace context.

### 2.2 Bridged Personal Accounts (`FamilyAccountShare`)
To support real-world households where a primary earner uses a personal bank account to settle household rent or utility bills, ARTHSAVORA implements the **Selective Account Sharing Bridge**:
- An individual member explicitly bridges an existing personal account into the family workspace.
- The personal account remains physically located in the user's personal workspace (`account.workspace_id == user_personal_ws.id`).
- The bridge record (`family_account_shares`) grants scoped read permissions inside the family workspace.

---

## 3. Account Sharing Scopes

The account owner selects the degree of transparency granted to household members:

| Share Scope | Balance Visible | Transaction History Visible | Allocation Eligibility | Description |
| :--- | :---: | :---: | :---: | :--- |
| `BALANCE_ONLY` | Yes | No | Yes (as payment source) | Members can see the aggregate balance to know if funds are available for bills, but cannot view line items. |
| `READ_ONLY` | Yes | Yes (Filtered) | Yes | Members can view transactions associated with shared categories (groceries, rent, bills), while private line items remain masked. |
| `FULL_VISIBILITY` | Yes | Yes (Complete) | Yes | Members can view all transactions and statements for this specific account within the family workspace context. |

---

## 4. Revocation and Safety Invariants

### 4.1 Owner-Controlled Revocation
A bridged personal account can be unshared at any time by the account owner or a Family Workspace Owner/Admin. Revoking a bridge:
1. Immediately invalidates the `FamilyAccountShare` record (`is_active = FALSE`, `revoked_at = NOW()`).
2. Stops all future visibility of that account within the family workspace.
3. **Preserves Personal Ledger:** All underlying transactions in the owner's personal workspace remain intact and uninterrupted.
4. **Preserves Historical Allocations:** Historical expense allocations and settlements that referenced this account remain immutable for historical audit and accounting balance integrity.

### 4.2 Anti-Coercion and Privacy Guarantees
- No family member—regardless of role (even Workspace Owner)—can force another member to share a personal account.
- Invitation to a family workspace cannot be made conditional on account disclosure at the protocol level.
- Minors and restricted members cannot view unshared personal accounts or bridge their own accounts without explicit parental confirmation.
