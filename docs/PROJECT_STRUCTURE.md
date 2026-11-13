# ARTHSAVORA — PROJECT STRUCTURE

**Document Reference:** `docs/PROJECT_STRUCTURE.md`  
**Current Architecture:** Modular Monolith with pnpm Workspaces  
**Last Updated:** Prompt 02  

---

## 1. HIGH-LEVEL REPOSITORY LAYOUT

```text
Arthsavora/
├── apps/
│   ├── web/                        # React 18 + TypeScript + Vite Web Client
│   ├── mobile/                     # React Native + Expo Mobile Client (Planned)
│   └── admin/                      # Operations & Risk Console (Planned)
│
├── packages/
│   ├── contracts/                  # Shared TypeScript API Request/Response DTOs
│   ├── validation/                 # Shared Zod Schemas for Client & Edge
│   ├── design-tokens/              # Commercial FinTech Design Primitives
│   └── utilities/                  # Currency (INR) and Date Formatting Helpers
│
├── backend/
│   ├── app/
│   │   ├── core/                   # Config, Security, Logging, Exceptions
│   │   ├── api/                    # Master Router & HTTP Middleware
│   │   ├── modules/                # Domain Business Modules
│   │   ├── infrastructure/         # DB (PostgreSQL / Legacy Motor) & Storage
│   │   └── workers/                # Celery Background Processing (Planned)
│   ├── tests/                      # Pytest Async Test Suite
│   ├── requirements.txt            # Python Dependencies
│   └── pyproject.toml              # Ruff & Pytest Settings
│
├── docs/                           # Architectural, Audit, and Governance Docs
├── .github/
│   └── workflows/                  # GitHub Actions CI Automation
├── pnpm-workspace.yaml             # Monorepo Workspace Definitions
└── package.json                    # Monorepo Orchestration Scripts
```

---

## 2. APPS DIRECTORY

### `apps/web/`
- **Role:** Web client for personal, family, and small-business accounts.
- **Tech Stack:** React 18, TypeScript 5, Vite 7, Tailwind CSS 3, Zustand, TanStack Query, React Hook Form, Zod, Sonner.
- **Internal Layout:**
  - `src/app/`: Providers (QueryProvider), environment configuration, and app initialization.
  - `src/components/ui/`: Reusable, accessible UI components (Button, Card, Input, Badge, Skeleton).
  - `src/components/layout/`: Global navigation (`AppLayout`), headers, and responsive structures.
  - `src/components/feedback/`: Non-blocking feedback (`ErrorBoundary`, `EmptyState`).
  - `src/pages/`: Authenticated feature screens (`Dashboard`, `Expenses`, `Budget`, `Goals`, `Reports`, `Auth`).
  - `src/store/`: Typed Zustand stores (`useAuthStore`, `useExpenseStore`).
  - `src/lib/`: Typed Axios client (`api`), utility helpers (`cn`).

---

## 3. PACKAGES DIRECTORY

Shared, independently verifiable packages managed through pnpm workspace:

1. **`@arthsavora/contracts`:** Single source of truth for API contracts, pagination structures, and financial entities.
2. **`@arthsavora/validation`:** Zod schemas for input validation across forms and API boundaries.
3. **`@arthsavora/design-tokens`:** WCAG AAA compliant colors, spacing scales, border radii, and typographic tokens.
4. **`@arthsavora/utilities`:** INR currency formatters (`formatINR`), paise-to-rupee converters, and date utilities.

---

## 4. BACKEND DIRECTORY

### `backend/app/`
- **`core/`:**
  - `config.py`: Validated Pydantic settings with sensible defaults for local development.
  - `exceptions.py`: Standard application exception hierarchy (`ArthsavoraException`).
  - `logging.py`: Structured application logger.
  - `security.py`: Password hashing (bcrypt) and signed JWT tokens with UTC timestamps.
  - `dependencies.py`: Unified dependency injection for auth and DB sessions.
- **`api/`:**
  - `router.py`: Centralized router mounting `/api/auth`, `/api/expenses`, `/api/budget`, `/api/goals`, `/api/analytics`, `/api/ml`, `/api/reports`.
  - `middleware/`: Hardened CORS, request latency auditing, and global exception handlers.
- **`infrastructure/`:**
  - `database/base.py`: SQLAlchemy 2 declarative base with UUID primary keys and audit mixins.
  - `database/session.py`: Asynchronous PostgreSQL connection pool (`asyncpg`).
