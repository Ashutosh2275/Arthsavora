# ARTHSAVORA — Unified Frontend Architecture

**Document Reference:** `docs/FRONTEND_ARCHITECTURE.md`  
**Authoritative Standard:** Stage 5/6 Frontend Engineering  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Executive Summary & Vision

ARTHSAVORA is an institutional-grade, multi-entity financial intelligence platform designed for individuals, collaborative families, and small enterprises in India. The frontend architecture is built with a singular design objective: **uncompromising financial data integrity, instant responsiveness, deterministic isolation across workspaces, and a cohesive, premium user experience**.

The application operates as a high-performance Single Page Application (SPA) structured within a Turborepo-managed monorepo. It interfaces with ARTHSAVORA's asynchronous Python/FastAPI ledger and intelligence engine while strictly enforcing zero client-side calculation drift, full double-entry balance verification, and strict multi-tenant authorization boundaries.

---

## 2. Monorepo Structure & Package Boundaries

ARTHSAVORA utilizes `pnpm` workspaces coordinated via Turborepo. Shared concerns are partitioned into immutable package boundaries to prevent code duplication, circular dependencies, and type drift:

```
Arthsavora/
├── apps/
│   └── web/                     # React 19 / Vite Application Shell & Feature Pages
└── packages/
    ├── contracts/               # TypeScript DTOs, API Requests/Responses, Enums
    ├── utilities/               # Pure formatting, currency math (paise), date calculations
    ├── design-tokens/           # Color palettes, typography, spacing, border radii
    └── validation/              # Zod validation schemas matching backend Pydantic models
```

### Monorepo Boundaries & Constraints
1. **Zero UI dependencies in `@arthsavora/contracts`:** Contracts define pure data transfer schemas and types. No DOM, React, or browser APIs are permitted.
2. **Deterministic paise calculations in `@arthsavora/utilities`:** All monetary math uses integer paise (`1 INR = 100 paise`). Floating-point arithmetic is prohibited for ledger-authoritative values.
3. **Canonical Styling in `@arthsavora/design-tokens`:** Design tokens define the raw visual constants imported by Tailwind CSS configurations and CSS custom properties.

---

## 3. Technology Stack & Runtime Specifications

| Layer | Technology | Version | Architectural Responsibility |
| :--- | :--- | :--- | :--- |
| **Runtime & Framework** | React | 19.x | Component lifecycle, concurrent rendering, error boundary isolation |
| **Build & Bundler** | Vite | 7.x | High-speed ESM dev server, Rollup production bundling, chunk optimization |
| **Language** | TypeScript | 5.8+ | Strict null checks, exhaustive union typing, no implicit any |
| **Styling & Design System**| Tailwind CSS | 3.4+ | Utility-first CSS, dark-mode class strategy, CSS variables |
| **Icons & Visuals** | Lucide React | Latest | Consistent 24px/16px vector icon system |
| **State Management** | Zustand | 5.x | Lightweight, decoupled stores with cross-workspace invalidation |
| **Routing** | React Router DOM | 6.x | Client-side routing, protected route boundaries, query parameter sync |
| **Testing Engine** | Vitest & Testing Library | 5.x / 16.x | JSDOM isolated test runners, accessible selector assertions |

---

## 4. Layered Architectural Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Shell Layer                   │
│         (AppLayout, TopBar, Sidebar, GlobalSearch)          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                     Routing & Page Layer                    │
│   (Dashboard, Ledger, Accounts, Budgets, Forecast, etc.)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                   Domain State & Stores                     │
│    (useWorkspaceStore, useThemeStore, useTransactionStore)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    API Client & Gateway                     │
│         (apiClient, interceptors, X-Workspace-ID)           │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                ARTHSAVORA REST API Backend                  │
│       (FastAPI, PostgreSQL 18, Ledger & Financial Engine)   │
└─────────────────────────────────────────────────────────────┘
```

### Core Architectural Invariants:
1. **Unidirectional Data Flow:** Data enters the application via authenticated REST endpoints through typed API clients, populates domain stores, and flows downwards into presentation components via props and custom hooks.
2. **Multi-Tenant Context Propagation:** Every outgoing HTTP request automatically receives the active workspace identifier via the `X-Workspace-ID` header.
3. **Workspace Invalidation Hooks:** When switching workspaces, all data stores trigger registered eviction callbacks to wipe in-memory state and force immediate re-fetching.
4. **Resilient Error Containment:** Feature-level and global React error boundaries catch unhandled exceptions, rendering contextual fallbacks without terminating the entire application shell.

---

## 5. Security & Isolation Boundaries

- **Authentication Storage:** Session tokens and refresh tokens are managed via secure, HttpOnly cookies where supported, with in-memory access token mirrors in `useAuthStore`.
- **Zero Cross-Workspace Contamination:** Workspaces are strictly isolated. State stores register with the `workspaceChangeListeners` bus in `useWorkspaceStore.ts` and clear records on tenant change.
- **XSS & Injection Mitigation:** All user-controlled text is sanitized before rendering. CSV exports and cell displays sanitize formula injection triggers (`=`, `+`, `-`, `@`).
