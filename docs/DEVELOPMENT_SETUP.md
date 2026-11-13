# ARTHSAVORA — LOCAL DEVELOPMENT SETUP

**Document Reference:** `docs/DEVELOPMENT_SETUP.md`  
**Last Updated:** Prompt 02  

This guide provides instructions to run, test, and develop the Arthsavora ecosystem locally.

---

## 1. PREREQUISITES

- **Node.js:** v20+ (v22 recommended)
- **pnpm:** v12+ (`corepack enable` or `npm install -g pnpm`)
- **Python:** v3.11+
- **PostgreSQL:** v15+ (optional for initial offline mode)
- **Git**

---

## 2. REPOSITORY INITIALIZATION

```bash
# 1. Clone the repository
git clone https://github.com/Ashutosh2275/Arthsavora.git
cd Arthsavora

# 2. Install workspace dependencies
pnpm install

# 3. Setup backend environment file
cp backend/.env.example backend/.env

# 4. Setup frontend environment file
cp apps/web/.env.example apps/web/.env
```

---

## 3. RUNNING THE APPLICATIONS

### Web Client (`apps/web`)

```bash
# Start development server on http://localhost:5173
pnpm --filter @arthsavora/web dev

# Or from project root
pnpm dev:web
```

The web application proxies `/api` calls directly to `http://127.0.0.1:8000`.

### Backend Engine (`backend`)

```bash
# Navigate to backend directory
cd backend

# Install dependencies (if not globally available)
pip install -r requirements.txt

# Start FastAPI development server with hot reload
uvicorn app.main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`.  
Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

## 4. RUNNING QUALITY CHECKS AND TESTS

### Frontend Checks

```bash
# Typecheck all packages and the web application
pnpm -r run typecheck

# Lint the web application (ESLint)
pnpm --filter @arthsavora/web lint

# Build web application for production
pnpm --filter @arthsavora/web build
```

### Backend Checks

```bash
# Run backend test suite with Pytest
pytest backend/tests

# Check Python syntax and imports
python -m py_compile backend/app/main.py
```
