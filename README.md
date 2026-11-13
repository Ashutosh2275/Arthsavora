# ARTHSAVORA

> AI-Powered Financial Management Ecosystem Engineered for Commercial Use in India.

Arthsavora unifies personal, family, and small-business financial management into a single modular-monolith platform, combining automated transaction ingestion, double-entry ledger bookkeeping, predictive budgeting, and financial intelligence.

---

## Architecture Overview

- **Monorepo:** pnpm workspaces (`apps/*`, `packages/*`)
- **Web Client:** React 18 + TypeScript + Vite + Tailwind CSS (`apps/web`)
- **Backend Engine:** Python 3.11 + FastAPI (`backend`)
- **Persistence:** PostgreSQL (Primary Relational Source of Truth) via SQLAlchemy 2.0 (asyncpg)
- **Shared Contracts:** `@arthsavora/contracts`, `@arthsavora/validation`, `@arthsavora/design-tokens`, `@arthsavora/utilities`
- **CI/CD:** GitHub Actions (`.github/workflows/ci.yml`)

---

## Quick Start

### 1. Install Dependencies
```bash
pnpm install
```

### 2. Configure Environment
```bash
cp backend/.env.example backend/.env
cp apps/web/.env.example apps/web/.env
```

### 3. Start Development Servers

**Web Frontend:**
```bash
pnpm dev:web
# Runs on http://localhost:5173
```

**FastAPI Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
# Runs on http://localhost:8000
```

---

## Documentation

- [Repository Audit](docs/REPOSITORY_AUDIT.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Development Setup](docs/DEVELOPMENT_SETUP.md)
- [Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md)
- [Configuration Reference](docs/CONFIGURATION_REFERENCE.md)
- [Coding Standards](docs/CODING_STANDARDS.md)
- [Architecture Gap Register](docs/ARCHITECTURE_GAP_REGISTER.md)
- [Development Progress](docs/DEVELOPMENT_PROGRESS.md)
