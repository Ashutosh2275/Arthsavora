# ARTHSAVORA — CODING STANDARDS & BEST PRACTICES

**Document Reference:** `docs/CODING_STANDARDS.md`  
**Last Updated:** Prompt 02  

---

## 1. TYPESCRIPT & FRONTEND STANDARDS

1. **Zero `any`:** Never use `any`. Use `unknown`, generic parameters, or explicit interfaces from `@arthsavora/contracts`.
2. **Explicit Interfaces:** Define interfaces for all component props, API payloads, and state models.
3. **Path Aliases:** Use `@/*` pointing to `src/*` for all internal module imports.
4. **Non-Blocking UI:** Never use native browser dialogs (`window.alert()`, `window.confirm()`). Use `sonner` toast notifications or custom modal dialogs.
5. **Currency Presentation:** Always format currency numbers using `formatINR()` from `@arthsavora/utilities`. Never display raw numbers with hardcoded `₹` prefixes.

---

## 2. PYTHON & BACKEND STANDARDS

1. **Explicit Routing:** Route handlers must not contain SQL queries or business logic. They must delegate directly to domain services or repositories.
2. **Timezone-Aware Timestamps:** Prohibit `datetime.utcnow()`. Always use `datetime.now(timezone.utc)`.
3. **Pydantic Validation:** All incoming request bodies and outgoing responses must be strictly validated with Pydantic v2 schemas (`BaseModel`, `ConfigDict`).
4. **Standardized Error Responses:** Raise domain exceptions derived from `ArthsavoraException` in `app.core.exceptions`.

---

## 3. FINANCIAL INVARIANTS

1. **No Floating-Point Money:** Currency must be stored as `NUMERIC(18, 4)` in PostgreSQL or integer paise in minor units.
2. **Balanced Debits & Credits:** Double-entry journal entries must satisfy $\sum \text{Debits} = \sum \text{Credits}$.
3. **Audit Immutability:** Financial postings are immutable. Fix errors with reversal entries.
