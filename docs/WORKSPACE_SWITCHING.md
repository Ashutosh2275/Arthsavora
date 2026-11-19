# ARTHSAVORA — Multi-Tenant Workspace Switching Architecture

**Document Reference:** `docs/WORKSPACE_SWITCHING.md`  
**Authoritative Standard:** Stage 5/6 Multi-Entity Tenancy & State Isolation  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Executive Overview

ARTHSAVORA operates on a multi-entity workspace model where a single user identity can participate in multiple financial boundaries:
- **Personal Workspaces:** Sole proprietorship of individual personal finances.
- **Family Workspaces:** Multi-member household budgeting with strict member privacy and selective sharing.
- **Business Workspaces:** GST-compliant commercial finances, client/vendor invoicing, and AR/AP ledgers.

The frontend workspace switching engine (`useWorkspaceStore.ts` and `WorkspaceSwitcher.tsx`) guarantees **instant switching, zero data leakage across workspace boundaries, and seamless backend synchronization**.

---

## 2. Workspace State Management

The workspace store maintains the user's active tenant state and accessible workspace list:

```typescript
interface WorkspaceState {
  workspaces: WorkspaceResponse[];
  activeWorkspace: WorkspaceResponse | null;
  members: WorkspaceMemberResponse[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchWorkspaces: () => Promise<void>;
  setActiveWorkspace: (workspace: WorkspaceResponse) => void;
  createWorkspace: (name: string, type: 'personal' | 'family' | 'business', currency?: string) => Promise<WorkspaceResponse>;
  updateWorkspace: (id: string, updates: Partial<WorkspaceResponse>) => Promise<void>;
  fetchMembers: (workspaceId: string) => Promise<void>;
  inviteMember: (email: string, role: string) => Promise<void>;
  removeMember: (memberId: string) => Promise<void>;
}
```

Persistent storage retains the `active_workspace_id` in `localStorage` across page reloads.

---

## 3. The Cross-Workspace Cache Invalidation Architecture

To prevent dangerous financial data contamination (e.g., family transactions appearing in a business ledger), ARTHSAVORA implements an **event-driven cache eviction protocol**:

```
[User Selects New Workspace in WorkspaceSwitcher]
                        │
                        ▼
            setActiveWorkspace(workspace)
                        │
                        ▼
     Update localStorage('active_workspace_id')
                        │
                        ▼
   Trigger onWorkspaceChangeListeners() Dispatcher
  ┌─────────────────────┼─────────────────────┐
  ▼                     ▼                     ▼
useAccountStore   useTransactionStore   useReportStore
.resetState()     .resetState()         .resetState()
  │                     │                     │
  ▼                     ▼                     ▼
Fetch Accounts    Fetch Transactions    Fetch Statements
(with new ID)     (with new ID)         (with new ID)
```

### Store Invalidation Registration Pattern
Stores register cleanup callbacks with `useWorkspaceStore`:

```typescript
// Example: in useAccountStore or page initialization
useEffect(() => {
  const unsubscribe = registerWorkspaceChangeListener((newWorkspaceId) => {
    // Clear existing accounts immediately
    set({ accounts: [], isLoading: true });
    // Re-fetch under new tenancy boundary
    get().fetchAccounts(newWorkspaceId);
  });
  return unsubscribe;
}, []);
```

---

## 4. HTTP Gateway Tenancy Synchronization

Every outbound HTTP request routed through `apps/web/src/lib/api.ts` intercepts requests and injects the active workspace ID:

```typescript
apiClient.interceptors.request.use((config) => {
  const activeWorkspace = useWorkspaceStore.getState().activeWorkspace;
  if (activeWorkspace) {
    config.headers['X-Workspace-ID'] = activeWorkspace.id;
  }
  return config;
});
```

This guarantees that backend row-level security policies (RLS) and PostgreSQL tenant filters strictly scope database queries to the active workspace.

---

## 5. Workspace Switcher Component & UX

The `WorkspaceSwitcher.tsx` component is positioned prominently in the application's `TopBar`:
1. **Visual Entity Distinction:** Color-coded pills and icons distinguish Personal (Blue/User), Family (Green/Users), and Business (Purple/Briefcase) entities.
2. **Current Workspace Pill:** Always displays the active workspace name and badge.
3. **Dropdown Menu:** Lists all accessible workspaces grouped by type, with a checkmark on the active entity.
4. **Create Workspace Modal:** Dedicated in-shell workflow allowing users to spin up a new Personal, Family, or Business entity with custom name and currency.
