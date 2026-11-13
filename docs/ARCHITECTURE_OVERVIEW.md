# ARTHSAVORA — ARCHITECTURE OVERVIEW

**Document Reference:** `docs/ARCHITECTURE_OVERVIEW.md`  
**Current Milestone:** Stage 1 Foundation  
**Last Updated:** Prompt 02  

---

## 1. ARCHITECTURAL PATTERN: MODULAR MONOLITH

Arthsavora adopts a **Modular Monolith** architecture for its core backend services and a **monorepo with package isolation** for its web and future mobile clients.

```text
┌────────────────────────────────────────────────────────┐
│                   CLIENT WORKSPACES                    │
│   apps/web (React 18 + TS)      apps/mobile (Expo)     │
└───────────────────────────┬────────────────────────────┘
                            │
              REST API / HTTPS / JSON DTOs
              (@arthsavora/contracts)
                            │
┌───────────────────────────▼────────────────────────────┐
│                FASTAPI BACKEND ENGINE                  │
│                                                        │
│  [API Middleware] ─► CORS, Request Audit, Error Format │
│                                                        │
│  [Master Router]  ─► /api/auth, /api/expenses,         │
│                      /api/budget, /api/goals, etc.     │
│                                                        │
│  [Core Services]  ─► Security, Config, Exceptions      │
│                                                        │
│  [Infrastructure] ─► PostgreSQL (SQLAlchemy 2.0 async) │
│                      Redis / Celery Workers            │
│                      Supabase Storage                  │
└────────────────────────────────────────────────────────┘
```

---

## 2. KEY ARCHITECTURAL PRINCIPLES

1. **PostgreSQL as Single Financial Source of Truth:**
   - Financial ledgers, multi-workspace accounts, journals, and balances reside exclusively in PostgreSQL.
   - Exact decimal precision (`NUMERIC(18, 4)` / integer paise) is enforced at all levels.
2. **Double-Entry Bookkeeping:**
   - Transactions are immutable sets of balanced debit and credit entries.
   - Corrections require explicit reversal entries; posted data is never mutated in place.
3. **Multi-Tenancy & Workspace Partitioning:**
   - All financial entities belong to a `workspace_id`.
   - Workspaces isolate personal households from freelance businesses and corporate entities.
4. **Asynchronous Non-Blocking Processing:**
   - Heavy tasks (time-series forecasting, OCR, PDF statement rendering) are offloaded to background workers, protecting the web event loop.
5. **Contract-Driven Development:**
   - Shared DTOs (`@arthsavora/contracts`) ensure strict type synchronization between client and server.
