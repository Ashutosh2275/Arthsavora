# ARTHSAVORA — ARCHITECTURE GAP REGISTER
**Document Reference:** `docs/ARCHITECTURE_GAP_REGISTER.md`  
**Audit Baseline:** Commit `6caa716456ec7cd9fff31ab16ee4a929b9f1d710`  
**Audit Date:** 2026-11-14  
**Total Identified Gaps:** 28  

This register documents every discrepancy between the existing Arthsavora implementation and the approved product architecture, financial requirements, security standards, and engineering specifications.

---

## GAP SUMMARY MATRIX

| Gap ID | Area | Title | Severity | Target Prompt |
| :--- | :--- | :--- | :--- | :--- |
| **GAP-001** | Database | Database Engine is MongoDB Instead of PostgreSQL | **CRITICAL** | Prompt 02 |
| **GAP-002** | Financial | Money Represented as Floating-Point (`float`) | **CRITICAL** | Prompt 02 |
| **GAP-003** | Financial | Absence of Double-Entry Ledger and Account Models | **CRITICAL** | Prompt 03 |
| **GAP-004** | Security | Insecure Wildcard CORS with Credentials Allowed | **CRITICAL** | Prompt 02 |
| **GAP-005** | Backend | Startup Crash Due to Mandatory Unconfigured Environment | **CRITICAL** | Prompt 02 |
| **GAP-006** | Financial | Budget Status Endpoint Groups All Historical Expenses | **CRITICAL** | Prompt 03 |
| **GAP-007** | Architecture | Lack of Multi-Tenancy & Workspace Partitioning | **CRITICAL** | Prompt 02 |
| **GAP-008** | Security | Tokens Insecurely Stored in Browser LocalStorage | **HIGH** | Prompt 04 |
| **GAP-009** | Frontend | Frontend Written in JavaScript (JSX) Instead of TypeScript | **HIGH** | Prompt 04 |
| **GAP-010** | Mobile | React Native / Expo Mobile Application Missing | **HIGH** | Prompt 18 |
| **GAP-011** | QA | Complete Absence of Automated Tests (0% Coverage) | **HIGH** | Prompt 02 |
| **GAP-012** | Background | Celery and Redis Background Processing Missing | **HIGH** | Prompt 06 |
| **GAP-013** | AI/ML | Synchronous ML Training and Disk I/O During Request Execution | **HIGH** | Prompt 07 |
| **GAP-014** | Security | Unbounded File Uploads & Memory Exhaustion Risk in OCR | **HIGH** | Prompt 08 |
| **GAP-015** | Security | Public Bucket Exposure of Confidential Financial Receipts | **HIGH** | Prompt 08 |
| **GAP-016** | Financial | Silent Hard Deletion of Financial Records (No Audit Trail) | **HIGH** | Prompt 03 |
| **GAP-017** | DevOps | Missing Git Hygiene: Tracked Bytecode (.pyc) in Git | **HIGH** | Prompt 02 |
| **GAP-018** | Frontend | Missing ESLint Configuration (Linting Fails) | **MEDIUM** | Prompt 02 |
| **GAP-019** | DevOps | Absence of CI/CD Automation (.github Workflows Missing) | **MEDIUM** | Prompt 05 |
| **GAP-020** | AI/ML | Deprecated Google Generative AI SDK & Legacy Model Name | **MEDIUM** | Prompt 09 |
| **GAP-021** | AI/ML | Prompt Injection Vulnerability in Financial Chatbot | **MEDIUM** | Prompt 09 |
| **GAP-022** | AI/ML | Hardcoded Mock Income (₹50k) Used for Financial Projections | **MEDIUM** | Prompt 09 |
| **GAP-023** | Integration | Hardcoded Windows Path for Tesseract Binary in OCR | **MEDIUM** | Prompt 08 |
| **GAP-024** | Quality | Abandoned Empty Placeholder Files (0 Bytes) | **LOW** | Prompt 04 |
| **GAP-025** | UI/UX | Frontend Endpoint Path Mismatch (/auth/login vs /api/auth/login)| **HIGH** | Prompt 04 |
| **GAP-026** | UI/UX | Native Blocking Window.alert() Used Across Frontend | **LOW** | Prompt 04 |
| **GAP-027** | Code Quality | Deprecated datetime.utcnow() Used Across Backend | **LOW** | Prompt 02 |
| **GAP-028** | Security | Outdated Frontend Dependencies (22 Vulnerabilities) | **MEDIUM** | Prompt 04 |

---

## DETAILED GAP SHEETS

### GAP-001: Database Engine is MongoDB Instead of PostgreSQL
- **Severity:** **CRITICAL**
- **Classification:** ARCHITECTURALLY INCOMPATIBLE
- **Module:** `backend/app/db/mongodb.py`
- **Evidence:** Lines 1-35 import `AsyncIOMotorClient` from `motor.motor_asyncio` and instantiate `db_instance.db = db_instance.client.arthsavora`. No PostgreSQL driver, SQLAlchemy engine, or Alembic configuration exists in the codebase.
- **Impact:** Commercial financial systems require ACID transactions, strict schema constraints, foreign key cascades, and point-in-time recovery. MongoDB lacks the relational integrity and accounting guarantees required by Arthsavora.
- **Recommended Action:** Scaffold PostgreSQL with SQLAlchemy 2 (asyncpg) and Alembic migrations. Re-implement models as relational tables.
- **Dependency:** None.
- **Target Prompt:** Prompt 02.

---

### GAP-002: Money Represented as Floating-Point (`float`)
- **Severity:** **CRITICAL**
- **Classification:** BROKEN
- **Module:** `backend/app/models/` (`expense.py`, `budget.py`, `goal.py`)
- **Evidence:**
  - `expense.py` line 9: `amount: float`
  - `budget.py` line 9: `limit: float`
  - `goal.py` lines 9-10: `target_amount: float`, `current_amount: float = 0.0`
- **Impact:** IEEE 754 floating-point numbers cannot accurately represent decimal currencies (e.g., `0.1 + 0.2 != 0.3`). This causes accumulating rounding errors, financial drift, and reconciliation failures in commercial fintech accounting.
- **Recommended Action:** Enforce exact decimal representations across all models and APIs using integer paise/cents or `Numeric(18, 4)` / Python `Decimal`.
- **Dependency:** GAP-001.
- **Target Prompt:** Prompt 02.

---

### GAP-003: Absence of Double-Entry Ledger and Account Models
- **Severity:** **CRITICAL**
- **Classification:** MISSING
- **Module:** `backend/app/models/`
- **Evidence:** The repository only defines ad-hoc `Expense`, `Budget`, and `Goal` collections. There are no entities for `Account` (Assets, Liabilities, Equity, Revenue, Expense), `JournalEntry`, `LedgerLine`, or `Transaction` with balanced debit/credit legs.
- **Impact:** Arthsavora cannot serve as a reliable financial source of truth. Transfers, loans, credit cards, reversals, and tax calculations cannot be audited or balanced.
- **Recommended Action:** Design and implement a double-entry ledger domain model enforcing the fundamental accounting equation ($\text{Assets} = \text{Liabilities} + \text{Equity}$).
- **Dependency:** GAP-001, GAP-002.
- **Target Prompt:** Prompt 03.

---

### GAP-004: Insecure Wildcard CORS with Credentials Allowed
- **Severity:** **CRITICAL**
- **Classification:** BROKEN
- **Module:** `backend/app/main.py`
- **Evidence:** Lines 48-53:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
      allow_headers=["*"],
  )
  ```
- **Impact:** Violates the W3C CORS specification. In compliant browsers, credentials (cookies, authorization headers) are blocked when origin is `*`. In non-compliant clients, it leaves the API open to cross-origin credentialed abuse.
- **Recommended Action:** Configure CORS to read allowed origins from environment settings with strict hostname checking for development and production domains.
- **Dependency:** None.
- **Target Prompt:** Prompt 02.

---

### GAP-005: Startup Crash Due to Mandatory Unconfigured Environment
- **Severity:** **CRITICAL**
- **Classification:** BROKEN
- **Module:** `backend/app/core/config.py`
- **Evidence:** Lines 4-21 enforce 5 non-defaulted strings (`MONGODB_URL`, `SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`). Top-level execution `settings = Settings()` raises an unhandled `pydantic_core.ValidationError` upon importing any backend module. No `.env.example` file exists.
- **Impact:** The backend cannot be imported, tested, built in CI, or run locally by a new developer without manual intervention.
- **Recommended Action:** Provide `.env.example`, sensible development defaults, and safe configuration handling for tests and documentation builds.
- **Dependency:** None.
- **Target Prompt:** Prompt 02.

---

### GAP-006: Budget Status Endpoint Groups All Historical Expenses
- **Severity:** **CRITICAL**
- **Classification:** BROKEN
- **Module:** `backend/app/api/budget.py`
- **Evidence:** Lines 44-48:
  ```python
  pipeline = [
      {"$match": {"user_id": uid}},
      {"$group": {"_id": "$category", "totalSpent": {"$sum": "$amount"}}}
  ]
  ```
- **Impact:** Aggregates every expense in the database history for the user against this month's budget. A user who has used the app for 6 months will show massive budget overruns instantly.
- **Recommended Action:** Constrain aggregation strictly between start-of-month and end-of-month UTC timestamps.
- **Dependency:** GAP-001.
- **Target Prompt:** Prompt 03.

---

### GAP-007: Lack of Multi-Tenancy & Workspace Partitioning
- **Severity:** **CRITICAL**
- **Classification:** MISSING
- **Module:** `backend/app/models/` and `backend/app/api/`
- **Evidence:** All models and queries filter solely on `user_id`. There is no `workspace_id` or `tenant_id`.
- **Impact:** Violates product positioning ("personal, family and small-business financial management ecosystem"). Users cannot maintain separate financial domains for household vs freelance business vs company books.
- **Recommended Action:** Introduce `Workspace` and `WorkspaceMember` models with role-based permissions (`Owner`, `Admin`, `Member`, `Bookkeeper`) and mandatory workspace scoping on all financial queries.
- **Dependency:** GAP-001.
- **Target Prompt:** Prompt 02.

---

### GAP-008: Tokens Insecurely Stored in Browser LocalStorage
- **Severity:** **HIGH**
- **Classification:** BROKEN
- **Module:** `frontend/src/api/axios.js`, `frontend/src/store/useAuthStore.js`
- **Evidence:** `localStorage.getItem('token')` and `localStorage.setItem('token', access_token)`.
- **Impact:** Susceptible to token theft via Cross-Site Scripting (XSS). In financial applications, access credentials must be stored in secure `HttpOnly`, `SameSite=Strict`, `Secure` cookies or managed session storage.
- **Recommended Action:** Transition authentication session management to secure cookies or Supabase session tokens with automated rotation.
- **Dependency:** GAP-005.
- **Target Prompt:** Prompt 04.

---

### GAP-009: Frontend Written in JavaScript (JSX) Instead of TypeScript
- **Severity:** **HIGH**
- **Classification:** ARCHITECTURALLY INCOMPATIBLE
- **Module:** `frontend/src/`
- **Evidence:** All source files use `.jsx` and `.js` extensions (`App.jsx`, `Dashboard.jsx`, `Expenses.jsx`, `axios.js`, `useAuthStore.js`). No `tsconfig.json` exists in `frontend/`.
- **Impact:** Lack of compile-time type safety leads to runtime crashes, type coercion bugs, and untyped financial data transformations.
- **Recommended Action:** Migrate frontend to TypeScript (`.tsx` and `.ts`), add `tsconfig.json`, and define strict interfaces for all API payloads and financial entities.
- **Dependency:** None.
- **Target Prompt:** Prompt 04.

---

### GAP-010: React Native / Expo Mobile Application Missing
- **Severity:** **HIGH**
- **Classification:** MISSING
- **Module:** Repository Root
- **Evidence:** Only `backend/` and `frontend/` directories exist. No `mobile/` or Expo project exists.
- **Impact:** Target platforms include Android and iOS. Essential Indian fintech capabilities (such as direct on-device SMS parsing) require a mobile runtime.
- **Recommended Action:** Scaffold a shared cross-platform React Native + Expo mobile application consuming shared TypeScript types and backend APIs.
- **Dependency:** GAP-009.
- **Target Prompt:** Prompt 18.

---

### GAP-011: Complete Absence of Automated Tests (0% Coverage)
- **Severity:** **HIGH**
- **Classification:** MISSING
- **Module:** Repository Root
- **Evidence:** `Test-Path backend/tests` and `Test-Path frontend/src/__tests__` both return `False`. Exactly zero test files exist.
- **Impact:** No automated safety net exists. Any code changes risk regressing existing calculations or introducing security flaws undetected.
- **Recommended Action:** Establish Pytest for backend (unit and integration) and Vitest + React Testing Library for frontend.
- **Dependency:** None.
- **Target Prompt:** Prompt 02.

---

### GAP-012: Celery and Redis Background Processing Missing
- **Severity:** **HIGH**
- **Classification:** MISSING
- **Module:** `backend/requirements.txt`, `backend/app/`
- **Evidence:** `celery` and `redis` are absent from `requirements.txt`. Heavy tasks (ReportLab PDF generation, openpyxl exports, ARIMA model fitting, IsolationForest detection, OCR) execute synchronously on the web process.
- **Impact:** Concurrent user requests freeze the FastAPI event loop, causing HTTP 504 timeouts and degraded user experience.
- **Recommended Action:** Integrate Celery with Redis broker for asynchronous background job execution.
- **Dependency:** None.
- **Target Prompt:** Prompt 06.

---

### GAP-013: Synchronous ML Training and Disk I/O During Request Execution
- **Severity:** **HIGH**
- **Classification:** BROKEN
- **Module:** `backend/app/services/ml/classifier.py`
- **Evidence:** Line 55 trains MultinomialNB on module import; line 70 runs `joblib.load(MODEL_PATH)` on every single prediction inside `predict()`.
- **Impact:** Severe disk I/O bottleneck and event loop blocking under concurrent load.
- **Recommended Action:** Keep model artifact in memory; train asynchronously offline or via background workers; serialize model loading into a singleton cache.
- **Dependency:** None.
- **Target Prompt:** Prompt 07.

---

### GAP-014: Unbounded File Uploads & Memory Exhaustion Risk in OCR
- **Severity:** **HIGH**
- **Classification:** BROKEN
- **Module:** `backend/app/api/ml_ops.py`
- **Evidence:** Line 23: `image_bytes = await file.read()` reads the entire file into server RAM without checking file size, magic bytes, or dimensions.
- **Impact:** Denial of Service (DoS) via memory exhaustion when an attacker uploads multi-gigabyte files.
- **Recommended Action:** Enforce max upload limit (e.g., 5MB), validate magic bytes (JPEG/PNG/PDF), and process files via streaming or temporary disk buffers.
- **Dependency:** None.
- **Target Prompt:** Prompt 08.

---

### GAP-015: Public Bucket Exposure of Confidential Financial Receipts
- **Severity:** **HIGH**
- **Classification:** BROKEN
- **Module:** `backend/app/core/supabase.py`
- **Evidence:** Line 25: `supabase_client.storage.from_("receipts").get_public_url(unique_name)`.
- **Impact:** Anyone with the URL can inspect sensitive personal financial receipts, merchant data, and bank slip details without authentication.
- **Recommended Action:** Make storage bucket private and generate short-lived signed URLs (`create_signed_url`) verified against user workspace permissions.
- **Dependency:** GAP-007.
- **Target Prompt:** Prompt 08.

---

### GAP-016: Silent Hard Deletion of Financial Records (No Audit Trail)
- **Severity:** **HIGH**
- **Classification:** BROKEN
- **Module:** `backend/app/api/expenses.py` (lines 36-48), `backend/app/api/goals.py` (lines 84-88)
- **Evidence:** Calls `db.expenses.delete_one({"_id": ObjectId(expense_id)})`. No `deleted_at` timestamp or change ledger entry.
- **Impact:** Financial transactions can be permanently purged, preventing tax auditing and opening opportunities for fraudulent tampering.
- **Recommended Action:** Implement soft deletes (`is_deleted`, `deleted_at`) and record an audit log entry for every state transition.
- **Dependency:** GAP-001.
- **Target Prompt:** Prompt 03.

---

### GAP-017: Missing Git Hygiene: Tracked Bytecode (.pyc) in Git
- **Severity:** **HIGH**
- **Classification:** BROKEN
- **Module:** `backend/app/**/__pycache__/`
- **Evidence:** 24 `.cpython-313.pyc` files are actively tracked in Git commit `6caa716456ec7cd9fff31ab16ee4a929b9f1d710`.
- **Impact:** Repository bloat, merge conflicts across Python minor versions, and leakage of build host metadata.
- **Recommended Action:** Remove tracked `.pyc` files from git cache and update `.gitignore` with `**/__pycache__/` and `*.py[cod]`.
- **Dependency:** None.
- **Target Prompt:** Prompt 02.

---

### GAP-018: Missing ESLint Configuration (Linting Fails)
- **Severity:** **MEDIUM**
- **Classification:** BROKEN
- **Module:** `frontend/`
- **Evidence:** Executing `npm run lint` yields: `ESLint couldn't find a configuration file.`
- **Impact:** Code quality regressions and syntax inconsistencies cannot be automatically detected in CI.
- **Recommended Action:** Provide `.eslintrc.cjs` or `eslint.config.js` tailored for React + TypeScript.
- **Dependency:** GAP-009.
- **Target Prompt:** Prompt 02.

---

### GAP-019: Absence of CI/CD Automation (.github Workflows Missing)
- **Severity:** **MEDIUM**
- **Classification:** MISSING
- **Module:** Repository Root
- **Evidence:** `.github/` folder does not exist.
- **Impact:** Code can be pushed to `main` without automated linting, type-checking, vulnerability scanning, or test execution.
- **Recommended Action:** Create GitHub Actions workflow for pull requests and main branch commits executing backend pytest, frontend typecheck, and linting.
- **Dependency:** GAP-011, GAP-018.
- **Target Prompt:** Prompt 05.

---

### GAP-020: Deprecated Google Generative AI SDK & Legacy Model Name
- **Severity:** **MEDIUM**
- **Classification:** EXISTING BUT NEEDS IMPROVEMENT
- **Module:** `backend/app/services/ml/chatbot.py`
- **Evidence:** Line 1 imports `google.generativeai` (emits official sunset warning); line 11 specifies legacy `'gemini-pro'`.
- **Impact:** Upstream Google API updates will eventually decommission this library and model endpoint.
- **Recommended Action:** Migrate to the new official `google-genai` SDK and modern models (`gemini-2.5-flash`).
- **Dependency:** None.
- **Target Prompt:** Prompt 09.

---

### GAP-021: Prompt Injection Vulnerability in Financial Chatbot
- **Severity:** **MEDIUM**
- **Classification:** BROKEN
- **Module:** `backend/app/services/ml/chatbot.py`
- **Evidence:** Lines 14-31 interpolate raw `user_query` directly into the prompt without delimiter guarding or sanitization.
- **Impact:** An attacker can manipulate the prompt to extract other context, alter recommendations, or produce misleading financial output.
- **Recommended Action:** Enforce system instruction separation and structured input boundaries with strict guardrails.
- **Dependency:** GAP-020.
- **Target Prompt:** Prompt 09.

---

### GAP-022: Hardcoded Mock Income (₹50k) Used for Financial Projections
- **Severity:** **MEDIUM**
- **Classification:** BROKEN
- **Module:** `backend/app/api/goals.py`
- **Evidence:** Lines 40-41 (`estimated_income = 50000`), line 72 (`surplus = 50000 - total_spent`).
- **Impact:** Financial milestone timelines and surplus investment recommendations show fictitious data to real users.
- **Recommended Action:** Derive real surplus from posted revenue/salary ledger entries or explicit user budget baseline profiles.
- **Dependency:** GAP-003.
- **Target Prompt:** Prompt 09.

---

### GAP-023: Hardcoded Windows Path for Tesseract Binary in OCR
- **Severity:** **MEDIUM**
- **Classification:** BROKEN
- **Module:** `backend/app/services/ocr/scanner.py`
- **Evidence:** Line 9: `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`.
- **Impact:** OCR crashes on Linux, macOS, Docker containers, or any system where Tesseract is installed in a different location.
- **Recommended Action:** Read path from environment variable (`TESSERACT_PATH`) with graceful fallback and clear error reporting.
- **Dependency:** None.
- **Target Prompt:** Prompt 08.

---

### GAP-024: Abandoned Empty Placeholder Files (0 Bytes)
- **Severity:** **LOW**
- **Classification:** PARTIALLY IMPLEMENTED
- **Module:** `backend/app/services/` and `frontend/src/`
- **Evidence:** Six 0-byte files:
  - `backend/app/services/recommendations.py`
  - `backend/app/services/report_gen.py`
  - `frontend/src/hooks/useAuth.js`
  - `frontend/src/hooks/useExpenses.js`
  - `frontend/src/utils/currency.js`
  - `frontend/src/utils/date.js`
- **Impact:** Confuses developers and litters the codebase with dead references.
- **Recommended Action:** Implement canonical utility helpers or remove placeholders during refactoring.
- **Dependency:** None.
- **Target Prompt:** Prompt 04.

---

### GAP-025: Frontend Endpoint Path Mismatch (/auth/login vs /api/auth/login)
- **Severity:** **HIGH**
- **Classification:** BROKEN
- **Module:** `frontend/src/store/useAuthStore.js`
- **Evidence:** Lines 17 & 35 post to `/auth/login` and `/auth/signup`, while backend routers in `main.py` line 56 are prefixed with `/api/auth`.
- **Impact:** Direct API calls fail with 404 Not Found if `VITE_API_URL` does not include the `/api` prefix.
- **Recommended Action:** Standardize all frontend API client calls with `/api` prefix or configure Axios `baseURL` consistently.
- **Dependency:** None.
- **Target Prompt:** Prompt 04.

---

### GAP-026: Native Blocking Window.alert() Used Across Frontend
- **Severity:** **LOW**
- **Classification:** EXISTING BUT NEEDS IMPROVEMENT
- **Module:** `frontend/src/` (`axios.js`, `Auth.jsx`, `Expenses.jsx`, `Goals.jsx`, `Reports.jsx`)
- **Evidence:** Multiple calls to `alert(...)`.
- **Impact:** Disrupts user flow, degrades perceived product quality, and fails commercial fintech UI/UX standards.
- **Recommended Action:** Implement accessible, non-blocking toast notifications (e.g., Sonner).
- **Dependency:** GAP-009.
- **Target Prompt:** Prompt 04.

---

### GAP-027: Deprecated datetime.utcnow() Used Across Backend
- **Severity:** **LOW**
- **Classification:** EXISTING BUT NEEDS IMPROVEMENT
- **Module:** `backend/app/` (`security.py`, `auth.py`, `models/expense.py`, `models/budget.py`, `goals.py`, `analytics.py`)
- **Evidence:** Widespread usage of `datetime.utcnow()`.
- **Impact:** Deprecated in Python 3.12+; generates deprecation warnings and risks timezone misalignment bugs in financial ledgers.
- **Recommended Action:** Replace with timezone-aware `datetime.now(timezone.utc)`.
- **Dependency:** None.
- **Target Prompt:** Prompt 02.

---

### GAP-028: Outdated Frontend Dependencies (22 Vulnerabilities)
- **Severity:** **MEDIUM**
- **Classification:** EXISTING BUT NEEDS IMPROVEMENT
- **Module:** `frontend/package.json`
- **Evidence:** `npm audit` reports 22 vulnerabilities (1 low, 7 moderate, 14 high), including Axios prototype pollution and Vite dev server file disclosure issues.
- **Impact:** Security vulnerabilities in third-party libraries risk client-side tampering and supply chain exposure.
- **Recommended Action:** Upgrade Axios to modern secure releases, patch devDependencies, and audit lockfile.
- **Dependency:** None.
- **Target Prompt:** Prompt 04.
