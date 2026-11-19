# ARTHSAVORA — Frontend Error Handling & Resilience Architecture

**Document Reference:** `docs/FRONTEND_ERROR_HANDLING.md`  
**Authoritative Standard:** Stage 5/6 Error Handling & Fault Containment  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Architectural Principles

In a commercial financial application, client errors must never result in a blank screen, unexplained data loss, or silent failure of critical operations. ARTHSAVORA enforces four core error containment principles:
1. **Compartmentalized Failure Domains:** Component failures are isolated to their immediate feature boundary using React Error Boundaries.
2. **Transparent, Actionable User Feedback:** Users are informed of what went wrong and provided an explicit recovery action (e.g., Retry, Refresh, or Contact Support).
3. **Structured API Error Normalization:** HTTP error codes (400, 401, 403, 404, 422, 500) are parsed systematically into user-readable error notifications.
4. **Zero Financial Drift on Network Failure:** Mutating actions (e.g. posting a journal entry or submitting an invoice) utilize optimistic UI rollbacks or require explicit server confirmation before committing local state.

---

## 2. React Error Boundary Layering

ARTHSAVORA layers error boundaries at multiple levels:

```
┌─────────────────────────────────────────────────────────────┐
│                    Root Error Boundary                      │
│      (Catches fatal shell crashes, offers hard reload)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    Route Error Boundary                     │
│      (Catches unhandled page exceptions, retains Shell)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                   Widget Error Boundaries                   │
│   (Catches chart/table rendering errors, renders fallback)  │
└─────────────────────────────────────────────────────────────┘
```

When a child component throws during render, the boundary renders an accessible fallback:
```tsx
<div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-6 text-center space-y-3">
  <AlertCircle className="mx-auto text-rose-400" size={32} />
  <h3 className="font-semibold text-rose-200">Unable to load financial widget</h3>
  <p className="text-xs text-rose-300">An unexpected error occurred while rendering this data.</p>
  <Button variant="outline" size="sm" onClick={() => resetErrorBoundary()}>
    Retry Widget
  </Button>
</div>
```

---

## 3. Network & API Error Normalization

In `apps/web/src/lib/api.ts`, response interceptors normalize errors into a uniform error shape:

```typescript
export interface NormalizedApiError {
  status: number;
  message: string;
  code?: string;
  fieldErrors?: Record<string, string[]>;
}
```

### Response Code Matrix:
- **401 Unauthorized:** Clears session tokens, notifies `useAuthStore`, and redirects to login.
- **403 Forbidden:** Displays an alert: *"You do not have permission to perform this action in this workspace."*
- **422 Unprocessable Entity:** Automatically maps Pydantic/FastAPI validation detail arrays into form field error messages.
- **429 Rate Limited:** Displays an alert: *"Too many requests. Please wait a moment before trying again."*
- **500+ Internal Server Error:** Logs error diagnostics to console/monitoring and renders a user-friendly generic failure alert.

---

## 4. Form Validation & Error Prevention

1. **Client-Side Schema Validation:** Forms validate input data against Zod schemas from `@arthsavora/validation` prior to network dispatch.
2. **Deterministic Amount Parsing:** Number inputs for financial sums prevent decimal drift by converting user input to integer paise immediately (`Math.round(rupees * 100)`). Negative numbers are disallowed on debit/credit magnitude fields.
3. **Double-Submission Prevention:** Action buttons automatically toggle to `isLoading={true}` and `disabled={true}` while async mutations are in flight.
